import cmd
import types
from datetime import datetime
import importlib
from importlib import util
import inspect
import os
import time
import sys
import traceback
from pathlib import Path
from typing import Any
import javascript.connection

import numpy
from deap import algorithms
from deap import base
from deap import creator
from deap import tools
from deap import gp
from deap.algorithms import eaSimple

import swarmcraft.btree.nodes.base as bt
from swarmcraft.btree.nodes.actuation import StartDig, PressDir, Look, ReleaseDir
from swarmcraft.btree.nodes.sensing import CanDigBlock
from agents import forage


def sequence_1_child(child1):
    return bt.SequenceNode([child1])

def sequence_2_child(child1, child2):
    return bt.SequenceNode([child1, child2])

def sequence_3_child(child1, child2, child3):
    return bt.SequenceNode([child1, child2, child3])

def fallback_1_child(child1):
    return bt.FallbackNode([child1])

def fallback_2_child(child1, child2):
    return bt.FallbackNode([child1, child2])

def fallback_3_child(child1, child2, child3):
    return bt.FallbackNode([child1, child2, child3])

creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)

# Class for color of type string
class WoolColor(str):
    pass

def generate_pset(agents):
    """
    Creates the Primitive Set (PSet) for DEAP.
    Nodes are mapped to 0-arity primitives (leaves) to handle arguments.
    Adjusted gp.generate to handle tree generation correctly. Missing prim and term raised errors.
    """
    pset = gp.PrimitiveSetTyped("MAIN", [], bt.ControlNode)

    # Branches
    pset.addPrimitive(sequence_1_child, [bt.BehaviorTreeNode], bt.ControlNode)
    pset.addPrimitive(sequence_2_child, [bt.BehaviorTreeNode, bt.BehaviorTreeNode], bt.ControlNode)
    pset.addPrimitive(sequence_3_child, [bt.BehaviorTreeNode, bt.BehaviorTreeNode, bt.BehaviorTreeNode], bt.ControlNode)
    pset.addPrimitive(fallback_1_child, [bt.BehaviorTreeNode], bt.ControlNode)
    pset.addPrimitive(fallback_2_child, [bt.BehaviorTreeNode, bt.BehaviorTreeNode], bt.ControlNode)
    pset.addPrimitive(fallback_3_child, [bt.BehaviorTreeNode, bt.BehaviorTreeNode, bt.BehaviorTreeNode], bt.ControlNode)

    # functions for Dig
    def make_dig(color):
        return StartDig(agents, color)
    def make_sense(color):
        return CanDigBlock(agents, color)

    # Primitives for Dig
    pset.addPrimitive(make_dig, [WoolColor], bt.ActionNode, name="Dig")
    pset.addPrimitive(make_sense, [WoolColor], bt.ActionNode, name="CanDig")
    # The wool color constants for Dig
    pset.addTerminal("blue_wool", WoolColor, name="BlueWool")
    pset.addTerminal("orange_wool", WoolColor, name="OrangeWool")

    #pset.addTerminal(StartDig(agents), bt.BehaviorTreeNode, name="Dig") # Digs everything
    pset.addTerminal(Look(agents), bt.ActionNode, name="Look")
    pset.addTerminal(PressDir(agents), bt.ActionNode, name="Move")
    pset.addTerminal(ReleaseDir(agents), bt.ActionNode, name="Stop")
    #pset.addTerminal(CanDigBlock(agents), bt.BehaviorTreeNode, name="CanDig") # Looks for anything that can be dug

    return pset

def set_toolbox(pset, population_count):
    toolbox = base.Toolbox()
    toolbox.register("expr", gp.genGrow, pset=pset, min_=1, max_=2) # first tree
    toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("compile", gp.compile, pset=pset)
    # --- GA Configuration ---
    # Modified for Population = 1
    if population_count > 1:
        tournsize = round(population_count/10) if round(population_count/10)>2 else 3 if population_count > 3 else population_count
        toolbox.register("select", tools.selTournament, tournsize=tournsize)
    else:
        toolbox.register("select", tools.selBest)  # Tournament doesn't work well with N=1
    toolbox.register("mate", gp.cxOnePoint)  # crossover for more than one individual?
    toolbox.register("expr_mut", gp.genGrow, min_=1, max_=2)  # leafs can have different depth # used for mutation
    toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
    return toolbox

def set_stats():
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", numpy.mean)
    stats.register("std", numpy.std)
    stats.register("max", numpy.max)
    return stats

#_nodes = [bt.SequenceNode, bt.FallbackNode, bt.ActionNode]
#_terminals = [PressDir, StartDig, ReleaseDir, CanDigBlock, Look]

from swarmcraft.experiment import Experiment
from swarmcraft.environment import Environment

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'logs'))

class ServerShell(cmd.Cmd):
    intro = "Shell for swarmcraft simulator. Type help or ? to list commands.\nType 'run' followed by generation, agent_count, number_runs_per_gen, population_count. All values as integers.\n"
    prompt = "swarmcraft > "
    file = None

    def __init__(self, server, pooler, messenger, envs_dir, exps_dir):
        super(ServerShell, self).__init__()
        self.server = server
        self.pooler = pooler
        self.messenger = messenger
        self.environments = {}
        self.experiments = {}
        self.envs_dir = envs_dir
        self.exps_dir = exps_dir
        self.load_envs(envs_dir)
        self.load_exps(exps_dir)
        self.running_experiment = None
        self.loaded_environment = None

    def load_envs(self, abs_dir):
        self.environments = {}
        print("Loading environments from", abs_dir)
        for env in os.listdir(abs_dir):
            if env.endswith('.py'): # all python files in environments dir are loaded
                spec = importlib.util.spec_from_file_location(f'envrionments.{env[:-3]}', os.path.join(abs_dir, env)) # initialize the import spec from the file
                mod = importlib.util.module_from_spec(spec) # then create the module based on that spec
                sys.modules[f'environments.{env[:-3]}'] = mod # add that module to the system modules
                try:
                    spec.loader.exec_module(mod) # execute the module (i think this initializes all classes in the file, in essence just runs the file)
                    for name, obj in inspect.getmembers(mod):
                        # look at all the things that got initialized
                        if inspect.isclass(obj) and issubclass(obj, Environment) and name != 'Environment':
                            # if those things are objects which are subclasses of the Environment class but not that original class, add them to the environments dict under their name
                            self.environments[name] = obj
                except Exception as e:
                    print('Failed to load environment:', e)
                    traceback.print_tb(e.__traceback__)
        print("Loaded environments:")
        for name, env in self.environments.items():
            print(f'\t{name}: {env}')

    def load_exps(self, abs_dir):
        self.experiments = {}
        print("Loading experiments from", abs_dir)
        for exp in os.listdir(abs_dir):
            if exp.endswith('.py'):
                spec = importlib.util.spec_from_file_location(f'experiments.{exp[:-3]}', os.path.join(abs_dir, exp))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f'experiments.{exp[:-3]}'] = mod
                try:
                    spec.loader.exec_module(mod)
                    for name, obj in inspect.getmembers(mod):
                        if inspect.isclass(obj) and issubclass(obj, Experiment) and name != 'Experiment':
                            self.experiments[name] = obj
                except Exception as e:
                    print('Failed to load experiment:', e)
                    traceback.print_tb(e.__traceback__)
        print("Loaded experiments:")
        for name, exp in self.experiments.items():
            print(f'\t{name}: {exp}')

    def cmdloop(self, intro: Any | None = None):
        try:
            super().cmdloop(intro)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            #super().cmdloop('')
            self.do_quit([])

    def do_reloadenvs(self, args):
        """Reload environments"""
        self.load_envs(self.envs_dir)

    def do_reloadexps(self, args):
        """Reload experiments"""
        self.load_exps(self.exps_dir)

    def do_lsbots(self, args):
        """List all bound and free bots"""
        print(f'Bound bots ({len(self.pooler.bound_bots)}):')
        for b in self.pooler.bound_bots:
            print("\t" + b.username)
        print(f'Free bots ({len(self.pooler.free_bots)}):')
        for b in self.pooler.free_bots:
            print("\t" + b.username)

    def do_addbot(self, args):
        """Add a new free bot"""
        at = args.split()
        if at:
            for i in range(int(at[0])):
                self.pooler.create_bot()
        else:
            self.pooler.create_bot()

    def do_resetbots(self, args):
        """Reset all free bots"""
        for b in self.pooler.free_bots:
            self.pooler.reset_bot_stats(b)
            self.pooler.reset_bot_position(b)

    def do_prunebots(self, args):
        """Remove all free bots"""
        while len(self.pooler.free_bots) > 0:
            b = self.pooler.free_bots.pop()
            b.quit()

    def do_run(self, args):
        """Run an experiment"""
        LOG_DIR = "./logs"
        at = args.split()
        exp_name = "ForageExperiment"
        exp_args = ['1']
        exp = None

        # Generations: how often should the individual evolve
        generations = int(at[0]) if len(at) > 0 else 5
        # Agent count: how many agents
        agent_count = int(at[1]) if len(at) > 1 else 1
        agent_count = 1
        # Number runs per environment: on how many envs should the controller be tested
        number_runs_per_gen = int(at[2]) if len(at) > 2 else 1
        # number of population
        population_count = int(at[3]) if len(at) > 3 else 5
        # which EA?
        simple = False # use eaSimple
        # crossover rate
        crossover_rate = 0.3
        # mutation probability
        mutation_prob = 0.5
        # global counter for current generation
        counter = 0

        if len(args) > 0:
            # Safety check if at is empty
            if at: num_runs = int(at[0])
        try:
            exp = self.experiments[exp_name](self.pooler, self.server, self.messenger, exp_args)
            exp.set_log_dir(Path(LOG_DIR) / f'{exp_name}-{datetime.now().strftime("%Y-%m-%d_%H-%M")}')

            # Initialize world and get agents
            # NOTE: Ensure 'agents' supports set_tree. If agents is a list, loop might be needed.
            agents = exp.initialize(agent_count)

            print("Set pset")
            pset = generate_pset(agents[0])
            print("Set toolbox")
            toolbox = set_toolbox(pset, population_count)

            # --- Define Evaluation Function (Closure) ---
            def evaluate_bt(individual, mission = "blue_wool", blocks = {'blue_wool': 4, 'orange_wool': 4, 'brown_wool': 0, 'green_wool': 0}):
                nonlocal counter

                # The first 'population_count' runs are Gen 0.
                # Everything after is part of the LAMBDA offspring cycles.
                if counter < population_count:
                    generation = 0
                    individual_idx = counter
                else:
                    # Subtract initial pop, then divide by LAMBDA to find the generation index
                    offset_counter = counter - population_count
                    generation = (offset_counter // LAMBDA) + 1
                    individual_idx = offset_counter % LAMBDA

                # Total expected individuals to evaluate
                total_individuals = population_count + (generations * LAMBDA)

                # Mission switch logic: halfway through the total expected evaluations
                if counter > total_individuals / 2:
                    mission = "orange_wool"

                print(f"Evaluation {counter + 1}/{total_individuals}")
                print(
                    f"Run generation {generation}/{generations} | Individual {individual_idx+1} of {population_count if generation == 0 else LAMBDA}")
                print(f"Mission: {mission} | Blocks: {blocks}")

                counter += 1

                print("Tree of Individual:", individual)

                new_tree = gp.compile(individual, pset)
                # Update the agents with the new behavior tree
                # NOTE: Ensure 'agents' supports set_tree. If agents is a list, loop might be needed.
                agents[0].set_tree(new_tree)
                # test controller on n environments
                fitness = 0
                for i in range(number_runs_per_gen):
                    #print(f"Testing individual {individual_count}: {i+1}/{number_runs_per_gen}")
                    #print(f"Testing Controller on environment {i+1}/{number_runs_per_env}")
                    # init arena, etc.
                    # decide on which blocks to randomly allocate in arena
                    # TODO Move the random generation of positions to another function. It should be possible to use the same environment 2+ times (really needed?)
                    exp.set_round(blocks)
                    # Run simulation
                    fitness += exp.run(mission, blocks)
                # average reward over n environments
                fitness = fitness/number_runs_per_gen

                try:
                    print("Tree: ", str(individual), " has fitness: ", fitness)
                except Exception as e:
                    print("Ind: ", individual, " err'd because ", e)
                return fitness,  # Tuple required

            toolbox.register("evaluate", evaluate_bt)

            pop = toolbox.population(n=population_count)
            hof = tools.HallOfFame(1)

            stats = set_stats()
            if population_count == 1:
                crossover_rate = 0
            while crossover_rate + mutation_prob > 1.0:
                crossover_rate -= 0.001
                mutation_prob -= 0.001
            # cxpb = 0 because crossover is impossible with 1 individual
            # mutpb = 1.0 implies we ALWAYS mutate the single agent (Random Walk)
            # mu=1 (keep 1 parent), lambda_=1 (generate 1 child), cxpb=0, mutpb=1.0
            print(f"Doing {generations + 1} runs with {agent_count} agents and {number_runs_per_gen} repetitions per generation.\nUsing {population_count} genomes with crossover rate {crossover_rate} and mutation probability {mutation_prob}")
            if simple:
                algorithms.eaSimple(pop, toolbox, cxpb=crossover_rate, mutpb=mutation_prob, ngen=generations, stats=stats, halloffame=hof, verbose=True)
            else:
                MU = population_count
                LAMBDA = MU * 3
                print(f"Using mu = {MU} and lambda = {LAMBDA}")
                algorithms.eaMuPlusLambda(pop, toolbox, mu=MU, lambda_=LAMBDA, cxpb=crossover_rate, mutpb=mutation_prob, ngen=generations, stats=stats, halloffame=hof)
            #print("Hof: ", hof)
            print("Result HOF: ", hof[0])
            exp.cleanup()

        except KeyError as e:
            print(f"Experiment '{exp_name}' not found: ", e)
        except Exception as e:
            print("Experiment error")
            print(e)
            traceback.print_tb(e.__traceback__)
            if exp is not None:
                try:
                    exp.cleanup()
                except Exception as cleanup_error:
                    print('Experiment cleanup error')
                    print(cleanup_error)


    def do_clear(self, args):
        """Clear an area"""
        at = args.split()
        res = self.server.send('setcube ' + str(self.pooler.WORLD_CENTER[0]) + ' ' + str(self.pooler.WORLD_CENTER[1]) + ' ' + str(self.pooler.WORLD_CENTER[2]) + ' ' + args)
        if res is not None: print(res)

    def do_cmd(self, args):
        """Send a minecraft command to the server
        See swarmcraft/minecraft/plugins/PySpigot/scripts/methods.py for available methods"""
        res = self.server.send('command ' + str(args))
        if res is not None: print(res)

    def do_do(self, args):
        """Send a swarmcraft command to the server"""
        res = self.server.send(str(args))
        if res is not None: print(res)

    def do_quit(self, args):
        """Stop the server and exit this shell"""
        print("Server going down...")
        """Stop the server and exit"""
        for b in self.pooler.bound_bots:
            b.quit()
        for b in self.pooler.free_bots:
            b.quit()
        self.server.stop()
        javascript.connection.stop()
        print("Server is DOWN!")
        return True

    def do_exit(self, args):
        """Alias for quit"""
        return self.do_quit(args)

    def do_readcube(self, args):
        """Read a cube and print the results to console"""
        at = args.split()
        blocks = self.server.send('getcube ' + args)
        if blocks is not None: print(blocks)

    def do_readblock(self, args):
        """Read a block and print the results to console"""
        at = args.split()
        block = self.server.send('getblock ' + args)
        if block is not None: print(block)

    def do_getlogdir(self):
        """Print the log directory"""
        print(LOG_DIR)

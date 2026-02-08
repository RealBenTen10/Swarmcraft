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
import random

import swarmcraft.btree.nodes.base as bt
from swarmcraft.btree.nodes.actuation import StartDig, PressDir, Look, ReleaseDir, SendMessage
from swarmcraft.btree.nodes.sensing import CanDigBlock, GotMessage
from swarmcraft.experiment import Experiment
from swarmcraft.environment import Environment

from swarm_gp import (
    register_control,
    register_action,
    instantiate_for_swarm,
    ea_mu_plus_lambda,
    tree_to_str,
    tree_length,
    reset_primitives,
)


#LOG_DIR = os.path.abspath(
#    os.path.join(os.path.dirname(__file__), os.pardir, "logs")
#)

# ============================================================
# BEHAVIOR TREE PRIMITIVE REGISTRATION (ONCE)
# ============================================================

def generate_pset():
    register_control(bt.SequenceNode, 2, 2) # only 2 children allowed
    register_control(bt.FallbackNode, 2, 2) # only 2 children allowed

    register_action(
        StartDig,
        param_generators=[lambda: random.choice(["blue_wool", "orange_wool"])]
    )
    register_action(
        CanDigBlock,
        param_generators=[lambda: random.choice(["blue_wool", "orange_wool"])]
    )
    register_action(Look)
    register_action(PressDir)
    register_action(ReleaseDir)
    register_action(
        SendMessage,
        param_generators=[lambda: random.choice([1,2])] # 2 kinds of messages
    )
    register_action(
        GotMessage,
        param_generators=[lambda: random.choice([1,2])] # 2 kinds of messages
    )



class ServerShell(cmd.Cmd):
    commands = "Type 'run' followed by swarm_size, generation, population_count, offspring_multiplyer (lambda = mu*n), \
    arena_count, run_duration, crossover, mutation, max_depth and min_depth."
    intro = f"Shell for swarmcraft simulator. Type help or ? to list commands.\n{commands}\nAll values as integers. Default values are set\n"
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

    def do_run(self, args):
        """
        Run an experiment with swarm-compatible genetic programming.

        Logging / Saving
        ---------------
        - Creates ./logging/run_N/ (N is the next free run id)
        - Writes ./logging/run_N/experiment_setup.txt
        - GP writes into the same run directory:
            ./logging/run_N/gp_log.csv
            ./logging/run_N/populations/gen_<g>.pkl
            ./logging/run_N/populations/latest.pkl
        """

        at = args.split()
        exp_name = "ForageExperiment"

        # ----------------------------
        # Parse CLI args (with defaults)
        # ----------------------------
        swarm_size = int(at[0]) if len(at) > 0 else 15
        generations = int(at[1]) if len(at) > 1 else 30

        population_count = int(at[2]) if len(at) > 2 else 15
        population_count = population_count if population_count > 1 else 2 # crossover needs at least 2 individuals

        offspring_multiplier = float(at[3]) if len(at) > 3 else 2.0
        lambda_ = int(round(population_count * offspring_multiplier)) # lambda needs to be an integer

        arena_count = int(at[4]) if len(at) > 4 else 4
        #arena_count = int(at[4]) if len(at) > 4 else max(1, 30 // swarm_size)
        #arena_count = min(arena_count, max(1, 30 // swarm_size))

        run_duration = int(at[5]) if len(at) > 5 else 30
        crossover_rate = float(at[6]) if len(at) > 6 else 0.4
        mutation_prob = float(at[7]) if len(at) > 7 else 0.2
        max_depth = int(at[8]) if len(at) > 8 else 2
        min_depth = int(at[9]) if len(at) > 9 else 1
        number_repetitions = int(at[10]) if len(at) > 10 else 1

        tournsize = int(at[11]) if len(at) > 11 else 3
        n_elites = int(at[12]) if len(at) > 12 else 1

        mission = "blue_wool"
        blocks = {
            "blue_wool": 4,
            "orange_wool": 4,
            "brown_wool": 0,
            "green_wool": 0,
        }

        # ----------------------------
        # Create ./logging/run_N folder
        # ----------------------------
        base_logging_dir = Path(os.getcwd()) / "logging"
        base_logging_dir.mkdir(parents=True, exist_ok=True)

        run_id = 0
        while (base_logging_dir / f"run_{run_id}").exists():
            run_id += 1

        run_dir = base_logging_dir / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=False)

        # ----------------------------
        # Save experiment setup text
        # ----------------------------
        setup_path = run_dir / "experiment_setup.txt"
        with open(setup_path, "w", encoding="utf-8") as f:
            f.write(f"timestamp: {datetime.now().isoformat()}\n")
            f.write(f"experiment: {exp_name}\n\n")

            f.write("=== swarm / evolution parameters ===\n")
            f.write(f"swarm_size: {swarm_size}\n")
            f.write(f"generations: {generations}\n")
            f.write(f"mu (population_count): {population_count}\n")
            f.write(f"offspring_multiplier: {offspring_multiplier}\n")
            f.write(f"lambda: {lambda_}\n")
            f.write(f"tournsize: {tournsize}\n")
            f.write(f"n_elites: {n_elites}\n")
            f.write(f"min_depth: {min_depth}\n")
            f.write(f"max_depth: {max_depth}\n")
            f.write(f"cxpb (crossover_rate): {crossover_rate}\n")
            f.write(f"mutpb (mutation_prob): {mutation_prob}\n")
            f.write(f"number_repetitions: {number_repetitions}\n\n")

            f.write("=== environment / experiment parameters ===\n")
            f.write(f"arena_count: {arena_count}\n")
            f.write(f"run_duration: {run_duration}\n")
            f.write(f"mission: {mission}\n")
            f.write(f"blocks: {blocks}\n")

        print("=== RUN CONFIG ===")
        print(f"Logging directory: {run_dir}")
        print(f"Generations: {generations}")
        print(f"Swarm size: {swarm_size}")
        print(f"Population size (mu): {population_count}")
        print(f"Offspring (lambda): {lambda_}")
        print(f"Arenas: {arena_count}")
        print(f"Run duration: {run_duration}")
        print(f"Crossover rate: {crossover_rate}")
        print(f"Mutation probability: {mutation_prob}")
        print(f"Min/Max depth: {min_depth} / {max_depth}")
        print(f"Tournament size: {tournsize}")
        print(f"Elites: {n_elites}")
        print(f"Repetitions: {number_repetitions}")
        print(f"Mission: {mission}")
        print(f"Blocks: {blocks}")

        current_gen = -1
        exp = None

        try:
            exp = self.experiments[exp_name](
                pooler=self.pooler,
                minecraft_server=self.server,
                message_server=self.messenger,
                run_duration=run_duration,
                arena_count=arena_count,
            )

            # Register primitives for THIS run (avoid duplicates across runs)
            reset_primitives()
            generate_pset()

            # Create agents once (exp.set_round resets env/agents state)
            agents = exp.initialize(swarm_size)

            # ====================================================
            # FITNESS FUNCTION (CONTROLLER-LEVEL)
            # ====================================================

            def evaluate_controller(tree, gen: int) -> float:
                nonlocal current_gen

                if gen != current_gen:
                    current_gen = gen
                    print(f"\n=== Generation {gen}/{generations} ===")

                print("Individual:", tree_to_str(tree))

                # Bind one copy per agent
                trees = instantiate_for_swarm(tree, agents)
                for agent, t in zip(agents, trees):
                    agent.set_tree(t)

                total_reward = 0.0
                for _ in range(number_repetitions):
                    exp.set_round(blocks)
                    total_reward += exp.run(mission, blocks)

                avg_reward = total_reward / float(number_repetitions)

                # Use swarm_gp.tree_length for penalty (same definition as logging)
                fitness_val = avg_reward - 0.01 * tree_length(tree)

                print("Fitness:", fitness_val)
                return fitness_val

            # ====================================================
            # EVOLUTION (WITH CSV LOGGING + POPULATION CHECKPOINTS)
            # ====================================================

            population = ea_mu_plus_lambda(
                mu=population_count,
                lambda_=lambda_,
                generations=generations,
                min_depth=min_depth,
                max_depth=max_depth,
                cxpb=crossover_rate,
                mutpb=mutation_prob,
                evaluate=evaluate_controller,
                tournsize=tournsize,
                n_elites=n_elites,
                logging_dir=run_dir,
            )

            best = population[0]
            print("\n=== RESULT ===")
            print("Best controller:", tree_to_str(best))
            print("Logs and populations saved in:", run_dir)
            exp.cleanup()

        except KeyError as e:
            print(f"Experiment '{exp_name}' not found:", e)

        except Exception as e:
            print("Experiment error:", e)
            traceback.print_tb(e.__traceback__)

        finally:
            try:
                if exp is not None:
                    exp.cleanup()
            except Exception as cleanup_error:
                print("Cleanup error:", cleanup_error)

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
        time.sleep(2)
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
        pass
        #print(LOG_DIR)

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
import json
from run_config import default_run_config, finalize_config, load_preset_config, apply_positional_overrides
from run_config import mission_for_generation

import swarmcraft.btree.nodes.base as bt
from swarmcraft.btree.nodes.actuation import StartDig, PressDir, Look, ReleaseDir, SendMessage
from swarmcraft.btree.nodes.sensing import CanDigBlock, GotMessage
from swarmcraft.experiment import Experiment
from swarmcraft.environment import Environment
from swarmcraft import BlockTypes

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
        param_generators=[lambda: random.choice([BlockTypes.BLUE_WOOL.value, BlockTypes.ORANGE_WOOL.value])]
    )
    register_action(
        CanDigBlock,
        param_generators=[lambda: random.choice([BlockTypes.BLUE_WOOL.value, BlockTypes.ORANGE_WOOL.value, BlockTypes.BEDROCK.value])]
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

        Configuration sources (precedence)
        ---------------------------------
        1) Defaults from default_run_config()
        2) Optional preset via: run --preset <id>
        3) Optional positional overrides (backward compatible)

        Logging / Saving
        ---------------
        - Creates ./logging/run_N/ (N is next free run id)
        - Writes ./logging/run_N/experiment_setup.txt (resolved config)
        - GP writes into the same run directory:
            ./logging/run_N/gp_log.csv
            ./logging/run_N/populations/gen_<g>.pkl
            ./logging/run_N/populations/latest.pkl
        """
        import json
        import traceback
        from pathlib import Path

        from run_config import (
            resolve_run_config,
            create_run_directories,
            print_run_config_summary,
        )

        # ============================================================
        # 1) Resolve configuration (defaults -> preset -> positional -> finalize)
        # ============================================================
        run_cfg = resolve_run_config(args)
        exp_name = run_cfg["exp_name"]

        # ============================================================
        # 2) Create run directory structure (./logging/run_N + populations/)
        # ============================================================
        run_meta = create_run_directories()  # defaults to ./logging
        run_cfg["run_id"] = run_meta["run_id"]
        run_cfg["run_dir"] = run_meta["run_dir"]
        run_cfg["pop_dir"] = run_meta["pop_dir"]
        run_cfg["timestamp"] = run_meta["timestamp"]

        run_dir = Path(run_cfg["run_dir"])

        # ============================================================
        # 3) Persist resolved setup
        # ============================================================
        setup_path = run_dir / "experiment_setup.txt"
        with setup_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(run_cfg, indent=2, sort_keys=True))

        # ============================================================
        # 4) Print resolved config summary
        # ============================================================
        print_run_config_summary(run_cfg)

        # ============================================================
        # 5) Execute experiment + GP
        # ============================================================
        exp = None
        current_gen = -1
        current_ind = 0

        population_count = run_cfg["population_count"]
        lambda_ = run_cfg["lambda_"]
        generations = run_cfg["generations"]

        try:
            exp = self.experiments[exp_name](
                pooler=self.pooler,
                minecraft_server=self.server,
                message_server=self.messenger,
                run_duration=run_cfg["run_duration"],
                arena_count=run_cfg["arena_count"],
                ORIGIN=run_cfg["arena_origin"],
                SIZE=run_cfg["arena_size"],
            )

            # Primitives must not accumulate across runs in the same process.
            reset_primitives()
            generate_pset()

            # Create agents once; exp.set_round() resets env/agents state per evaluation
            agents = exp.initialize(run_cfg["swarm_size"])

            # ----------------------------
            # Fitness function
            # ----------------------------
            def evaluate_controller(tree, gen: int) -> float:
                nonlocal current_gen, current_ind

                if gen != current_gen:
                    current_gen = gen
                    current_ind = 1
                    print(f"\n=== Generation {gen+1}/{run_cfg['generations']} | mission={mission_for_generation(run_cfg, gen)} ===")
                    # set new random block positions
                    exp.shuffle_block_positions(run_cfg["blocks"])
                else:
                    current_ind += 1

                # Bind one deepcopy per agent
                bound_trees = instantiate_for_swarm(tree, agents)
                for agent, t in zip(agents, bound_trees):
                    agent.set_tree(t)
                mission = mission_for_generation(run_cfg, gen)
                total_reward = 0.0
                for _ in range(run_cfg["number_repetitions"]):
                    exp.set_round()
                    total_reward += exp.run(mission, run_cfg["blocks"])

                avg_reward = total_reward / float(run_cfg["number_repetitions"])
                fitness_val = avg_reward - 0.01 * tree_length(tree)

                print(f"Individual {current_ind}/{population_count + lambda_}: {tree_to_str(tree)} has Fitness: {fitness_val}")
                return fitness_val

            # ----------------------------
            # Evolution
            # ----------------------------
            population = ea_mu_plus_lambda(
                mu=run_cfg["population_count"],
                lambda_=run_cfg["lambda_"],
                generations=run_cfg["generations"],
                min_depth=run_cfg["min_depth"],
                max_depth=run_cfg["max_depth"],
                cxpb=run_cfg["crossover_rate"],
                mutpb=run_cfg["mutation_prob"],
                evaluate=evaluate_controller,
                tournsize=run_cfg["tournsize"],
                n_elites=run_cfg["n_elites"],
                logging_dir=run_dir,  # gp_log.csv + populations/...
                resume_from=run_cfg["resume_from"],
            )

            print("\n=== RESULT ===")
            print("Best controller:", tree_to_str(population[0]))
            print("Logs and populations saved in:", run_dir)

        except KeyError as e:
            print(f"Experiment '{exp_name}' not found:", e)

        except Exception as e:
            print("Experiment error:", e)
            traceback.print_tb(e.__traceback__)

        finally:
            if exp is not None:
                try:
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

    def do_creative(self):
        self.server.send('command command /gamemode creative DarkRewind')

    def do_quit(self, args):
        """Stop the server and exit this shell"""
        print("Server going down...")
        """Stop the server and exit"""
        try:
            for b in self.pooler.bound_bots:
                b.quit()
        except:
            print("Couldn't quit bound bots")
        try:
            for b in self.pooler.free_bots:
                b.quit()
        except:
            print("Couldn't quit free bots")
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

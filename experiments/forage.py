import time
import threading
from typing import override
from collections import defaultdict
import numpy as np

import swarmcraft.util
from agents.forage import ForageAgent
from environments.forage import ForageEnvironment
from swarmcraft.experiment import Experiment


VALID_FITNESS_FUNCTIONS = {"S1", "S2", "S3", "S4"}

class ForageExperiment(Experiment):
    # Identical world layout for every experiment and every arena.
    ENVIRONMENT_BLOCKS = {"blue_wool": 9}

    def __init__(
        self,
        pooler,
        minecraft_server,
        message_server,
        run_duration=60,
        ORIGIN=(10, -60, 10),
        SIZE=(20, 10, 20),
        arena_count=1,
        arena_distance=20,
        fitness_function="S1",
        construction=False,
        *args
    ):
        super().__init__(pooler, minecraft_server, message_server)

        self.last_update_time = None
        self.update_interval = 0.5
        self.max_time_sec = run_duration

        self.arena_origin = ORIGIN
        self.arena_size = SIZE
        self.arena_count = arena_count
        self.arena_distance = arena_distance

        # Selects the fitness implementation in ForageAgent.
        self.fitness_function = fitness_function
        # Use this flag for
        self.construction = construction

        self.environments = []
        self.agents = []

        self.total_agents_existed = 0
        self.current_agent_count = 0

        #self.pooler.create_bot()

    def compute_arena_origin(self, arena_index: int):
        dx = arena_index * (self.arena_size[0] + self.arena_distance)
        return (
            self.arena_origin[0] + dx,
            self.arena_origin[1],
            self.arena_origin[2]
        )

    @override
    def initialize(self, agents_per_arena):
        self.minecraft_server.send("command gamerule doWeatherCycle false")
        self.minecraft_server.send("command weather clear 999999")
        self.minecraft_server.send("command gamerule doDaylightCycle false")
        self.minecraft_server.send("command time set day")
        self.last_update_time = time.time()



        # Clean up previous agents
        if self.agents:
            for agent in self.agents:
                self.pooler.unbind_bot(agent)

        self.agents = []
        self.environments = []


        for arena_idx in range(self.arena_count):
            origin = self.compute_arena_origin(arena_idx)

            env = ForageEnvironment(
                self.minecraft_server,
                origin,
                self.arena_size
            )
            env.clean_environment(20, 8)

            # Generate the deterministic layout once per environment.
            # Every round reuses exactly these positions.
            env.shuffle_block_positions(self.ENVIRONMENT_BLOCKS)
            self.environments.append(env)

            center = (
                origin[0] + self.arena_size[0] // 2,
                origin[1] + 1,
                origin[2] + self.arena_size[2] // 2,
            )
            time.sleep(0.0001)
            for _ in range(agents_per_arena):
                agent = ForageAgent(
                    self.pooler,
                    self.message_server,
                    f'forager_{self.total_agents_existed}',
                    center,
                    env,
                    fitness_function=self.fitness_function
                )
                self.total_agents_existed += 1
                self.current_agent_count += 1
                self.agents.append(agent)
        time.sleep(0.1)
        for env in self.environments:
            time.sleep(0.001)
            env.build_static_structures_once()

        for i in range(len(self.environments)-1):
            time.sleep(0.0001)
            self.environments[i].build_bridge_to(self.environments[i+1].origin)

        for agent in self.agents:
            time.sleep(0.0001)
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
            agent.get_bot(uid=agent.id)
            agent.reset()
        self.minecraft_server.send('say initialized multi-arena foraging environment')
        return self.agents

    def _set_agent_inventories(self, item_id: str = "", amount: int = 0):
        """
        Clears each agent's inventory and equips them with the required blocks.
        """
        for agent in self.agents:
            username = agent.sensing.get_username()
            self.minecraft_server.send(f'command clear {username}')
            time.sleep(0.005)
            if amount > 0:
                self.minecraft_server.send(f'command give {username} {item_id} {amount}')
            time.sleep(0.005)

    def set_round(self):
        for agent in self.agents:
            if agent.bot is None:
                if len(self.pooler.free_bots) == 0:
                    self.pooler.create_bot()
                    time.sleep(0.0001)
                agent.get_bot(uid=agent.id)
                time.sleep(0.0001)
            agent.reset()
            time.sleep(0.001)

        # Always start with a clean inventory.
        # Construction is the only experiment that receives blocks.
        if self.construction:
            self._set_agent_inventories(
                item_id="blue_wool",
                amount=1
            )

        for env in self.environments:
            time.sleep(0.001)
            env.reset_arena_interior()
            time.sleep(0.001)
            env.set_blocks()

    def shuffle_block_positions(self):
        # Kept for compatibility, but the actual layout is experiment-fixed.
        # Calling this explicitly regenerates the same deterministic layout.
        for env in self.environments:
            env.shuffle_block_positions(self.ENVIRONMENT_BLOCKS)


    @override
    def run(self):
        # Teleport each agent to its own arena center
        for agent in self.agents:
            x, y, z = agent.start_location
            self.minecraft_server.send(
                f'command tp {agent.sensing.get_username()} {x} {y} {z}'
            )
            time.sleep(0.01)
        for agent in self.agents:
            # ensure all bots look in the same direction
            agent.actuation.look((0, 0))
            time.sleep(0.01)

        time.sleep(1)

        start_time = time.time()

        def agent_worker(agent):
            """Worker loop executed by each agent's dedicated thread."""
            while time.time() - start_time < self.max_time_sec:
                tick_start = time.time()

                # Update agent behavior tree
                agent.update()

                # Calculate sleep duration to maintain self.update_interval without drifting
                elapsed = time.time() - tick_start
                sleep_time = self.update_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        # 1. Spawn one persistent thread for each agent
        threads = []
        for agent in self.agents:
            thread = threading.Thread(target=agent_worker, args=(agent,))
            threads.append(thread)
            thread.start()

        # 2. Wait for all agent threads to finish the run
        for thread in threads:
            thread.join()


        time.sleep(4) # wait before evaluation

        # Evaluate per arena and aggregate
        total_fitness = 0.0
        fitness = 0
        for env in self.environments:
            agents_in_env = [a for a in self.agents if a.environment is env]
            if not agents_in_env:
                continue
            for agent in agents_in_env:
                time.sleep(0.01)
                try:
                    fitness = agent.evaluation()
                    break
                except Exception as e:
                    print("Failed to get remaining blocks: ", e)

            total_fitness += fitness

        for agent in self.agents:
            agent.reset()
            time.sleep(0.001)
        return total_fitness / self.arena_count

    @override
    def cleanup(self):
        # Unbind bots first
        for agent in self.agents:
            self.pooler.unbind_bot(agent=agent)
            time.sleep(0.05)

        # Remove all built structures and restore flatness
        for env in self.environments:
            env.cleanup(radius=15, clear_height=6)
            time.sleep(0.01)

        # Clear references
        self.agents = []
        self.environments = []



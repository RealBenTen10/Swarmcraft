import time
import threading
from typing import override
from collections import defaultdict
import numpy as np

import swarmcraft.util
from agents.forage import ForageAgent
from environments.construct import ConstructionEnvironment
from swarmcraft.experiment import Experiment


class ConstructionExperiment(Experiment):
    def __init__(
        self,
        pooler,
        minecraft_server,
        message_server,
        run_duration=60,
        ORIGIN=(10, -60, 10),
        SIZE=(20, 10, 20),
        arena_count=1,
        arena_distance=10,
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

        self.environments = []
        self.agents = []

        self.total_agents_existed = 0
        self.current_agent_count = 0

    def compute_arena_origin(self, arena_index: int):
        dx = arena_index * (self.arena_size[0] + self.arena_distance)
        return (
            self.arena_origin[0] + dx,
            self.arena_origin[1],
            self.arena_origin[2]
        )

    def _set_agent_inventories(self, item_id: str = "141", amount: int = 3):
        """
        Clears each agent's inventory and equips them with the required blocks.
        """
        for agent in self.agents:
            username = agent.sensing.get_username()
            self.minecraft_server.send(f'command clear {username}')
            time.sleep(0.005)
            self.minecraft_server.send(f'command give {username} {item_id} {amount}')
            time.sleep(0.005)

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

            env = ConstructionEnvironment(
                self.minecraft_server,
                origin,
                self.arena_size
            )
            env.clean_environment(20, 8)
            self.environments.append(env)

            # Center position of the arena floor
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
                    f'builder_{self.total_agents_existed}',
                    center,  # Spawns at arena center
                    env
                )
                self.total_agents_existed += 1
                self.current_agent_count += 1
                self.agents.append(agent)

        time.sleep(0.1)
        for env in self.environments:
            time.sleep(0.001)
            env.build_static_structures_once()

        for i in range(len(self.environments) - 1):
            time.sleep(0.0001)
            self.environments[i].build_bridge_to(self.environments[i + 1].origin)

        for agent in self.agents:
            time.sleep(0.0001)
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
            agent.get_bot(uid=agent.id)
            agent.reset()

        # Give 3 blue_wool blocks to each agent
        self._set_agent_inventories(item_id="blue_wool", amount=3)

        self.minecraft_server.send('say initialized multi-arena construction environment')
        return self.agents

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

        # Reset inventory for each agent at start of round
        self._set_agent_inventories(item_id="blue_wool", amount=3)

        for env in self.environments:
            time.sleep(0.001)
            env.reset_arena_interior()
            time.sleep(0.001)
            env.set_blocks()

    def shuffle_block_positions(self, blocks):
        for env in self.environments:
            env.shuffle_block_positions(blocks)

    @override
    def run(self, mission, blocks, number_arena=None):
        # Teleport each agent to its arena center
        for agent in self.agents:
            x, y, z = agent.start_location
            self.minecraft_server.send(
                f'command tp {agent.sensing.get_username()} {x} {y} {z}'
            )
            time.sleep(0.01)

        for agent in self.agents:
            # Ensure all bots look in the same initial direction
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

        # Spawn one persistent thread for each agent
        threads = []
        for agent in self.agents:
            thread = threading.Thread(target=agent_worker, args=(agent,))
            threads.append(thread)
            thread.start()

        # Wait for all agent threads to finish the run
        for thread in threads:
            thread.join()

        time.sleep(2)  # Wait before completion

        for agent in self.agents:
            agent.reset()
            time.sleep(0.001)

        # Placeholder fitness value to be updated later
        total_fitness = 0.0
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
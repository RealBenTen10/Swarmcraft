import time
from typing import override

import numpy as np

import swarmcraft.util
from agents.forage import ForageAgent
from environments.forage import ForageEnvironment
from swarmcraft.experiment import Experiment



class ForageExperiment(Experiment):
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
        self.update_interval = 2.0
        self.max_time_sec = run_duration

        self.arena_origin = ORIGIN
        self.arena_size = SIZE
        self.arena_count = arena_count
        self.arena_distance = arena_distance

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
            env.clean_environment(20, 6)
            self.environments.append(env)

            center = (
                origin[0] + self.arena_size[0] // 2,
                origin[1] + 1,
                origin[2] + self.arena_size[2] // 2,
            )

            for _ in range(agents_per_arena):
                agent = ForageAgent(
                    self.pooler,
                    self.message_server,
                    f'forager_{self.total_agents_existed}',
                    center,
                    env
                )
                self.total_agents_existed += 1
                self.current_agent_count += 1
                self.agents.append(agent)
        for env in self.environments:
            env.build_static_structures_once()
        for agent in self.agents:
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
            agent.get_bot(uid=agent.id)
            agent.reset()
        self.minecraft_server.send('say initialized multi-arena foraging environment')
        return self.agents

    def set_round(self, blocks):
        for agent in self.agents:
            if agent.bot is None:
                if len(self.pooler.free_bots) == 0:
                    self.pooler.create_bot()
                agent.get_bot(uid=agent.id)
            agent.reset()
            time.sleep(0.05)

        for env in self.environments:
            env.reset_arena_interior()
            env.set_blocks(blocks)


    @override
    def run(self, mission, blocks, number_arena=None):
        # Teleport each agent to its own arena center
        for agent in self.agents:
            x, y, z = agent.start_location
            self.minecraft_server.send(
                f'command tp {agent.sensing.get_username()} {x} {y} {z}'
            )
            time.sleep(0.01)

        time.sleep(1)

        start_time = time.time()
        while time.time() - start_time < self.max_time_sec:
            if time.time() - self.last_update_time > self.update_interval:
                for agent in self.agents:
                    agent.update()
                self.last_update_time = time.time()

        # Evaluate per arena and aggregate
        # Evaluate per arena and aggregate
        total_fitness = 0.0
        for env in self.environments:
            agents_in_env = [a for a in self.agents if a.environment is env]
            if not agents_in_env:
                continue

            reference_agent = agents_in_env[0]

            remaining_blocks = reference_agent.sensing.get_blocks_in_arena(
                env.origin,
                env.size,
                blocks
            )

            # aggregate unique visited positions across ALL agents in this arena
            visited: set[tuple[int, int, int]] = set()
            for a in agents_in_env:
                visited.update(a.positions)

            unique_positions_count = len(visited)

            fitness = reference_agent.evaluation(
                remaining_blocks=remaining_blocks,
                color=mission,
                initial_blocks=blocks,
                unique_positions_count=unique_positions_count
            )

            # print(f"Arena fitness: {fitness} (unique visited positions: {unique_positions_count})")
            total_fitness += fitness


        for agent in self.agents:
            agent.reset()
            time.sleep(0.01)
        return total_fitness / self.arena_count

    @override
    def cleanup(self):
        # Unbind bots first
        for agent in self.agents:
            self.pooler.unbind_bot(agent=agent)
            time.sleep(0.01)

        # Remove all built structures and restore flatness
        for env in self.environments:
            env.cleanup(radius=15, clear_height=6)
            time.sleep(0.05)

        # Clear references
        self.agents = []
        self.environments = []



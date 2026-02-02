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

        self.pooler.create_bot()

    def compute_arena_origin(self, arena_index: int):
        dx = arena_index * (self.arena_size[0] + self.arena_distance)
        return (
            self.arena_origin[0] + dx,
            self.arena_origin[1],
            self.arena_origin[2]
        )

    @override
    def initialize(self, agents_per_arena):
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
            env.reset()
            env.initialize()
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
        for agent in self.agents:
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
            agent.get_bot(uid=agent.id)
            agent.reset()
        self.minecraft_server.send('say initialized multi-arena foraging environment')
        return self.agents



    def set_round(self, blocks):
        for agent in self.agents:
            agent.reset()
            time.sleep(0.05)

        for env in self.environments:
            env.reset()
            env.initialize()
            env.set_blocks(blocks)


    @override
    def run(self, mission, blocks, number_arena=None):
        # Teleport each agent to its own arena center
        for agent in self.agents:
            x, y, z = agent.start_location
            self.minecraft_server.send(
                f'command tp {agent.sensing.get_username()} {x} {y} {z}'
            )

        time.sleep(1)

        start_time = time.time()
        while time.time() - start_time < self.max_time_sec:
            if time.time() - self.last_update_time > self.update_interval:
                for agent in self.agents:
                    agent.update()
                self.last_update_time = time.time()

        # Evaluate per arena and aggregate
        fitness = 0.0
        for env in self.environments:
            reference_agent = next(a for a in self.agents if a.environment is env)
            remaining_blocks = reference_agent.sensing.get_blocks_in_arena(
                env.origin,
                env.size,
                blocks
            )
            fitness += reference_agent.evaluation(remaining_blocks, mission, blocks)

        for agent in self.agents:
            agent.reset()
            #self.pooler.unbind_bot(agent)

        return fitness / self.arena_count


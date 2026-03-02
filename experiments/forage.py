import time
from typing import override
from collections import defaultdict
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
                    env
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

        use_normal_loop = True
        if use_normal_loop:
            start_time = time.time()
            last_update = time.time()
            while time.time() - start_time < self.max_time_sec:
                if last_update < time.time():
                    # set last_update directly to ensure every 0.5 seconds the agents are ticked
                    last_update = time.time() + self.update_interval
                    # update each gent (ticks trees)
                    for agent in self.agents:
                        agent.update()
        else:
            # special loop where we iterate over agents in blocks divided via environment
            start_time = time.monotonic()
            envs = list(self.environments)
            n_env = len(envs)
            if n_env == 0:
                return

            update_interval = self.update_interval
            slot = update_interval / n_env

            # Initialize per-environment phased schedules:
            t0 = time.monotonic()
            next_env_update = {env: t0 + i * slot for i, env in enumerate(envs)}

            while time.monotonic() - start_time < self.max_time_sec:
                now = time.monotonic()

                # Build env -> agents mapping in O(#agents) per tick.
                env_to_agents = defaultdict(list)
                for a in self.agents:
                    env_to_agents[a.environment].append(a)

                # Update environments whose time slot has arrived.
                for env in envs:
                    due = next_env_update[env]
                    if now >= due:
                        for agent in env_to_agents.get(env, ()):
                            agent.update()

                        # Advance schedule without drifting the phase:
                        # If we are late by multiple intervals, skip forward accordingly.
                        missed = int((now - due) // update_interval)
                        next_env_update[env] = due + (missed + 1) * update_interval

                # Small sleep prevents busy-waiting; tune as needed.
                time.sleep(0.001)


        # Evaluate per arena and aggregate
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
                    remaining_blocks = agent.sensing.get_blocks_in_arena(
                        env.origin,
                        env.size,
                        blocks
                    )
                    visited: set[tuple[int, int, int]] = set()
                    for a in agents_in_env:
                        time.sleep(0.001)
                        visited.update(a.positions)

                    unique_positions_count = len(visited)

                    fitness = agent.evaluation(
                        remaining_blocks=remaining_blocks,
                        size=self.arena_size,
                        color=mission,
                        initial_blocks=blocks,
                        unique_positions_count=unique_positions_count,
                    )
                    break
                except Exception as e:
                    print("Failed to get remaining blocks: ", e)

            # aggregate unique visited positions across ALL agents in this arena

            # print(f"Arena fitness: {fitness} (unique visited positions: {unique_positions_count})")
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



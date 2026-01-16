import time
from typing import override

import numpy as np

import swarmcraft.util
from agents.forage import ForageAgent
from environments.forage import ForageEnvironment
from swarmcraft.experiment import Experiment

ORIGIN = (10, -60, 10)
SIZE = (20, 10, 20)
START_LOCATION = (20, -57, 20)


class ForageExperiment(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.last_update_time = None
        self.update_interval = 0.5  # how many seconds to wait between experiment updates
        self.init_agent_count = 1
        self.max_time_sec = 60
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 1, 1, 10)
        self.total_agents_existed = 0
        self.current_agent_count = 0
        self.pooler.create_bot()
        self.agents = None

    @override
    def initialize(self, agent_count):
        super().initialize()  # initialize and reset environment
        self.minecraft_server.send('say initialized foraging environment')
        # print("Amount of agents: ", self.init_agent_count)

        self.last_update_time = time.time()

        self.agents = []
        if agent_count > 1:
            for i in range(agent_count):
                if len(self.pooler.free_bots) == 0:
                    self.pooler.create_bot()
                a = ForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION,
                                self.environment, tree=None)
                self.total_agents_existed += 1
                self.current_agent_count += 1
                a.reset()
                self.agents.append(a)
        else:
            self.agents = [ForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION,
                            self.environment, tree=None)]
        self.minecraft_server.send('say initialized foraging agents')
        return self.agents

    def set_agents(self):
        for agent in self.agents:
            agent.get_bot(uid=f'forager_{self.total_agents_existed}')
            agent.reset()

    def set_environment(self, blocks):
        self.environment.reset()
        self.environment.initialize()
        self.environment.set_blocks(blocks)

    def set_round(self, blocks):
        self.set_agents()
        self.set_environment(blocks)

    @override
    def run(self, mission, blocks):
        # teleport agents to center of arena
        for agent in self.agents:
            self.minecraft_server.send(
                f'command tp {agent.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')

        time.sleep(1) # to ensure agents starts when on ground and in arena
        start_time = time.time()
        while time.time() - start_time < self.max_time_sec:
            if time.time() - self.last_update_time > self.update_interval:  # controlled update
                for agent in self.agents:
                    agent.update()
                self.last_update_time = time.time()
        # fitness currently returns global reward (not per agent)
        fitness = 0
        for agent in self.agents:
            #print("Run finished... Evaluating")
            remaining_blocks = agent.sensing.get_blocks_in_arena(ORIGIN, SIZE, blocks)
            #print("Got: ", remaining_blocks)
            fitness = agent.evaluation(remaining_blocks, mission, blocks)
            #print("Resetting agent")
            agent.reset()
            #print("Unbinding bot")
            # Do I need this?
            self.pooler.unbind_bot(agent)
        return fitness

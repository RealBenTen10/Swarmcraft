import time
from typing import override

import numpy as np

import swarmcraft.util
from agents.forage import ForageAgent
from environments.forage import ForageEnvironment
from swarmcraft.experiment import Experiment

ORIGIN = (10, -60, 10)
SIZE = (20, 10, 20)
START_LOCATION = (20, -55, 20)

class ForageExperiment(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.last_update_time = None
        self.update_interval = 1. # how many seconds to wait between experiment updates
        self.init_agent_count = 1
        self.max_time_sec = 30
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 1, 1, 10)
        self.total_agents_existed = 0
        self.current_agent_count = 0
        self.pooler.create_bot()


    @override
    def initialize(self):
        super().initialize() # initialize and reset environment
        self.minecraft_server.send('say initialized foraging environment')
        bt = "seq(move, dig)"
        self.agents = []
        # print("Amount of agents: ", self.init_agent_count)
        for i in range(self.init_agent_count):

            a = ForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION, self.environment, tree=bt)
            a.get_bot(uid=f'forager_{self.total_agents_existed}')
            self.total_agents_existed += 1
            self.current_agent_count += 1
            a.reset()
            self.agents.append(a)
            # print(f"Name of {a.get_uid()} at {i}: ", a.sensing.get_username())
            #a.sensing.get_blocks_in_arena()
        self.minecraft_server.send('say initialized foraging agents')
        self.last_update_time = time.time()
        return self.agents

    @override
    def run(self):
        start_time = time.time()
        # teleport agents to center of arena
        for a in self.agents:
            self.minecraft_server.send(f'command tp {a.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')

        # TODO
        #   implement deap in a separate file
        #   let deep create a behavior tree and feed the fitness
        #   just translate deap BT to swarmcraft BT (input and output doesn't matter)
        #   Open questions:
        #   what nodes do I need?
        #   How do I connect walk and sense blocks correctly (also include type of block)
        #   For beginning just two types of wool
        #   One current mission the other negative points
        #
        while self.current_agent_count > 0 and time.time() - start_time < self.max_time_sec:
            if time.time() - self.last_update_time > self.update_interval: # controlled update
                for a in self.agents:
                    a.update()

                # do logging
                self.log_agents()
                self.write_to_experiment_log({'time': time.time(), 'agents': self.current_agent_count})

                self.last_update_time = time.time()
        for a in self.agents:
            print("Run finished... Evaluating")
            remaining_blocks = a.sensing.get_blocks_in_arena()
            print("Got: ", remaining_blocks)
            fitness = a.sensing.evaluation(remaining_blocks, "blue_wool", 16)
            print("Resetting agent")
            a.reset()
            print("Unbinding bot")
            self.pooler.unbind_bot(a)
            print("Destroying agent")
            a.destroy()

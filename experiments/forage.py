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
decay_rate = 1 # how much health per second do agents lose?

class ForageExperiment(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.last_update_time = None
        self.update_interval = 1. # how many seconds to wait between experiment updates
        self.reproduction_threshold = 16. # how much health an agent needs to reproduce
        self.reproduction_cost = 10. # how much it costs to reproduce
        self.start_health = 6. # how much health new agents start with
        self.init_agent_count = 1
        self.max_time_sec = 30
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 1, 1, 10)
        self.total_agents_existed = 0
        self.current_agent_count = 0

    @override
    def initialize(self):
        super().initialize() # initialize and reset environment
        self.minecraft_server.send('say initialized foraging environment')

        self.agents = []
        print("Amount of agents: ", self.init_agent_count)
        for i in range(self.init_agent_count):
            self.pooler.create_bot()
            print("Agent count: ", self.total_agents_existed)
            a = ForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION, self.environment)
            self.total_agents_existed += 1
            self.current_agent_count += 1
            a.reset()
            self.agents.append(a)
            print(f"Name of {a.get_uid()} at {i}: ", a.sensing.get_username())
            #self.minecraft_server.send(f'setphealth {a.sensing.get_username()} {self.start_health}')
        self.minecraft_server.send('say initialized foraging agents')
        self.last_update_time = time.time()

    @override
    def run(self):
        print('changes loaded')
        start_time = time.time()
        # teleport agents to center of arena
        for a in self.agents:
            self.minecraft_server.send(f'command tp {a.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')
        # loop for BT
        while self.current_agent_count > 0 and time.time() - start_time < self.max_time_sec:
            if time.time() - self.last_update_time > self.update_interval: # controlled update
                agents_not_dead = []
                for a in self.agents:
                    a.update() # let the agent do stuff

                    # apply food and damage - not needed for me
                    '''
                    min_dist = np.inf  # figure distance to nearest resource
                    for pos in self.environment.resource_positions:
                        min_dist = min(min_dist, swarmcraft.util.dist_sqr(a.sensing.get_position(), pos))
                    bonus = (1. / max(min_dist, 0.005))  # how much bonus health? (at most 20)
                    # apply bonus
                    self.minecraft_server.send(f'changephealth {a.sensing.get_username()} {bonus}')
                    # apply damage
                    self.minecraft_server.send(f'command damage {a.sensing.get_username()} {decay_rate}')
                    # obviously it's nicer and probably a little quicker to say something like change = bonus - decay_rate
                    # but changephealth provides no visual feedback - with damage at least you know something happened
                    '''
                    # if the agent died after damage application, remove them and skip to the next agent
                    if a.sensing.has_died():
                        print(a.sensing.get_username(), 'died')
                        a.actuation.stop()
                        a.reset()
                        a.destroy()
                        self.current_agent_count -= 1
                        continue

                    # reproduce if we are able to and not dead yet - not needed for me
                    '''
                    if a.sensing.get_health() >= self.reproduction_threshold:
                        self.minecraft_server.send(f'say {a.sensing.get_username()} wants to reproduce')
                        if len(self.pooler.free_bots) > 0: # if there are bots available
                            # reproduce (just initialize a new bot here since we're not doing mutations)
                            child = ForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION, self.environment)
                            self.total_agents_existed += 1
                            self.current_agent_count += 1
                            child.reset()
                            agents_not_dead.append(child)
                            self.minecraft_server.send(f'setphealth {child.sensing.get_username()} {self.start_health}')
                            self.minecraft_server.send(f'command tp {child.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')
                            print(f"{a.sensing.get_username()} reproduced successfully")
                        else:
                            print(f"{a.sensing.get_username()}'s reproduction blocked (population full)")
                        self.minecraft_server.send(
                            f'command damage {a.sensing.get_username()} {self.reproduction_cost}')
                    '''
                    # keep this agent on the alive list
                    agents_not_dead.append(a)

                # once all agents have been updated, remember which ones are alive
                self.agents = agents_not_dead # move the reference

                # do logging
                self.log_agents()
                self.write_to_experiment_log({'time': time.time(), 'agents': self.current_agent_count})

                self.last_update_time = time.time()
        for a in self.agents:
            a.reset()
            self.pooler.unbind_bot(a)
            a.destroy()
        self.agents =[]

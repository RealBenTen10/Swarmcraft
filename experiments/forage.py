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
        self.num_agents = int(*args[0])
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 1, 1, 10)

    @override
    def initialize(self):
        super().initialize()
        self.environment.reset()
        self.environment.initialize()
        self.minecraft_server.send('say initialized foraging environment')

        self.agents = []
        for i in range(self.num_agents):
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
            a = ForageAgent(self.pooler, self.message_server, f'forager_{i}', START_LOCATION, self.environment)
            a.reset()
            self.agents.append(a)
            self.minecraft_server.send(f'setphealth {a.sensing.get_username()} {self.start_health}')
        self.minecraft_server.send('say initialized foraging agents')
        self.last_update_time = time.time()

    @override
    def run(self):
        start_time = time.time()
        for a in self.agents:
            self.minecraft_server.send(f'command tp {a.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')
        while time.time() - start_time < 30: #not self.done:
            # controlled update - once per second
            if time.time() - self.last_update_time > self.update_interval:
                for a in self.agents:
                    # update agent
                    a.update()

                    # apply food and damage
                    # distance to closest resource
                    min_dist = np.inf
                    for pos in self.environment.resource_positions:
                        min_dist = min(min_dist, swarmcraft.util.dist_sqr(a.sensing.get_position(), pos))
                    bonus = (1. / min_dist) # how much bonus health?
                    # apply bonus
                    self.minecraft_server.send(f'changephealth {a.sensing.get_username()} {bonus}')
                    # apply damage
                    self.minecraft_server.send(f'command damage {a.sensing.get_username()} {decay_rate}')
                    # obviously it's nicer and probably a little quicker to say something like change = bonus - decay_rate
                    # but changephealth provides no visual feedback - with damage at least you know something happened

                    # reproduce
                    if a.sensing.get_health() >= self.reproduction_threshold:
                        self.minecraft_server.send(f'say {a.sensing.get_username()} wants to reproduce')
                        self.minecraft_server.send(f'command damage {a.sensing.get_username()} {self.reproduction_cost}')
                self.last_update_time = time.time()

    @override
    def cleanup(self):
        super().cleanup()
        self.environment.reset()

    def done(self):
        blocks = self.minecraft_server.send(f'getcube {ORIGIN[0]} {ORIGIN[1]} {ORIGIN[2]} {SIZE[0]} {SIZE[1]} {SIZE[2]}')
        return not 'DIAMOND_BLOCK' in str(blocks) # done if the environment contains no more diamond blocks

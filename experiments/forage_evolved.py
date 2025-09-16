from copy import deepcopy
from typing import override
import time
import numpy as np

import swarmcraft.util
import swarmcraft.btree.genetics as genetics
from agents.forage import ForageAgent
from environments.forage import ForageEnvironment
from swarmcraft.experiment import Experiment

ORIGIN = (10, -60, 10)
SIZE = (20, 10, 20)
START_LOCATION = (20, -55, 20)

class ForageEvolved(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.last_update_time = None
        self.update_interval = 1. # how many seconds to wait between experiment updates
        self.reproduction_threshold = 16. # how much health an agent needs to reproduce
        self.reproduction_cost = 10. # how much it costs to reproduce
        self.start_health = 6. # how much health new agents start with
        self.decay_rate = 1 # how much health per second do agents lose?
        self.init_agent_count = int(*args[0])
        self.run_time = int(*args[1])
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 1, 1, 10)
        self.total_agents_existed = 0
        self.current_agent_count = 0

    @override
    def initialize(self):
        super().initialize()
        self.minecraft_server.send('say initialized foraging environment')

        # create twice as many bots as initial agents
        for _ in range(self.init_agent_count * 2):
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
        self.minecraft_server.send('say initialized bots')

        # set up initial agents
        self.agents = []
        for i in range(self.init_agent_count):
            a = ForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION, self.environment)
            self.total_agents_existed += 1
            self.current_agent_count += 1
            a.reset()
            self.agents.append(a)
            self.minecraft_server.send(f'setphealth {a.sensing.get_username()} {self.start_health}')
        self.minecraft_server.send('say initialized foraging agents')
        self.last_update_time = time.time()

        # set up the gene pool
        genetics.reset_terminals()


    @override
    def run(self):
        start_time = time.time()
        for a in self.agents:
            self.minecraft_server.send(f'command tp {a.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')
        while time.time() - start_time < self.run_time:
            if time.time() - self.last_update_time > self.update_interval:
                agents_not_dead = []
                for a in self.agents:
                    a.update()
                    # apply food and damage
                    min_dist = np.inf
                    for pos in self.environment.resource_positions:
                        min_dist = min(min_dist, swarmcraft.util.dist_sqr(a.sensing.get_position(), pos))
                    bonus = (1. / max(min_dist, 0.005)) # how much bonus health? (at most 20)
                    # apply bonus
                    self.minecraft_server.send(f'changephealth {a.sensing.get_username()} {bonus}')
                    # apply damage
                    self.minecraft_server.send(f'command damage {a.sensing.get_username()} {self.decay_rate}')
                    self.minecraft_server.send(f'say {a.sensing.get_username()}: gain {bonus}, lose {self.decay_rate}')
                    # obviously it's nicer and probably a little quicker to say something like change = bonus - decay_rate
                    # but this is more accurate
                    self.minecraft_server.send(f'command say {a.sensing.get_username()}: gain {bonus}, lose {self.decay_rate}')

                    # reproduce, with mutation
                    child = deepcopy(a) # reproduce
                    genetics.mutate(child.tree, child) # mutate the child's tree, bind the child's nodes to the child
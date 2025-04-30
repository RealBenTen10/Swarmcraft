import time
from time import sleep
from typing import override

from agents.forage import ForageAgent
from environments.forage_env import ForageEnvironment
from swarmcraft.experiment import Experiment
from swarmcraft.minecraft.server import minecraft_server
from swarmcraft.pooler import pooler
from util import add_tuples

ORIGIN = (10, 4, 10)
SIZE = (100, 10, 100)
START_LOCATION = (55, 5, 55)

class ForageExperiment(Experiment):
    def __init__(self, num_agents):
        super().__init__()
        self.num_agents = num_agents
        self.environment = ForageEnvironment(ORIGIN, SIZE, 2, 5, 20)

    @override
    def initialize(self):
        super().initialize()
        self.environment.reset()
        self.environment.initialize()
        minecraft_server.send('say initialized foraging environment')

        self.agents = []
        for i in range(self.num_agents):
            if len(pooler.free_bots) == 0:
                pooler.create_bot()
            a = ForageAgent(f'forager_{i}', START_LOCATION, self.environment)
            a.reset()
            self.agents.append(a)
            sleep(0.5) # whenever you create a new agent, you should sleep for at least 0.5, possibly more
            # this prevents a whole bunch of weird bugs
        minecraft_server.send('say initialized foraging agents')

    @override
    def run(self):
        start_time = time.time()
        while time.time() - start_time < 30: #not self.done:
            for a in self.agents:
                a.update()

    @override
    def cleanup(self):
        super().cleanup()
        self.environment.reset()

    def done(self):
        blocks = minecraft_server.read_cube(ORIGIN, add_tuples(ORIGIN, SIZE))
        return not 'DIAMOND_BLOCK' in str(blocks) # done if the environment contains no more diamond blocks


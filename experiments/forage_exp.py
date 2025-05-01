import time
from typing import override

from agents.forage import ForageAgent
from environments.forage_env import ForageEnvironment
from swarmcraft.experiment import Experiment

ORIGIN = (10, -60, 10)
SIZE = (100, 10, 100)
START_LOCATION = (55, 5, 55)

class ForageExperiment(Experiment):
    def __init__(self, num_agents, pooler, minecraft_server, message_server):
        super().__init__(pooler, minecraft_server, message_server)
        self.num_agents = num_agents
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 2, 5, 20)

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
            a = ForageAgent(f'forager_{i}', START_LOCATION, self.environment)
            a.reset()
            self.agents.append(a)
        self.minecraft_server.send('say initialized foraging agents')

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
        blocks = self.minecraft_server.send(f'getcube {ORIGIN[0]} {ORIGIN[1]} {ORIGIN[2]} {SIZE[0]} {SIZE[1]} {SIZE[2]}')
        return not 'DIAMOND_BLOCK' in str(blocks) # done if the environment contains no more diamond blocks


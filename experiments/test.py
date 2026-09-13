import time
from time import sleep
from typing import override

from agents.test import Tester
from swarmcraft.experiment import Experiment
from environments.custom import ForageEnvironment

ORIGIN = (10, -60, 10)

class Test(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, (50, 10, 50), 2, 5, 0)

    @override
    def initialize(self):
        self.environment.reset()
        self.environment.initialize()
        self.minecraft_server.send('say initialized foraging environment')

        if len(self.pooler.free_bots) == 0:
            self.pooler.create_bot()

        self.a = Tester(self.pooler, self.message_server, 'tester')
        self.a.reset()

    def run(self):
        print('start')
        start_time = time.time()
        self.minecraft_server.send(f'command tp {self.a.sensing.get_username()} 20 -58 20')
        sleep(1)
        self.minecraft_server.send(f'command give {self.a.sensing.get_username()} minecraft:grass_block 64')
        while time.time() - start_time < 30:
            self.a.update()

    def cleanup(self):
        super().cleanup()
        self.environment.reset()
        self.a.destroy()
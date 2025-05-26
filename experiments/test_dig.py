import time
from typing import override

from agents.test_dig import Digger
from swarmcraft.experiment import Experiment
from environments.forage import ForageEnvironment

ORIGIN = (10, -60, 10)

class DigTest(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, (50, 2, 50), 2, 5, 0)

    @override
    def initialize(self):
        self.environment.reset()
        self.environment.initialize()
        self.minecraft_server.send('say initialized foraging environment')

        if len(self.pooler.free_bots) == 0:
            self.pooler.create_bot()

        self.a = Digger(self.pooler, self.message_server, 'dig')
        self.a.reset()

    def run(self):
        start_time = time.time()
        self.minecraft_server.send(f'command tp {self.a.sensing.get_username()} 20 -55 20')
        while time.time() - start_time < 30:
            self.a.update()

    def cleanup(self):
        super().cleanup()
        self.environment.reset()
        self.a.destroy()
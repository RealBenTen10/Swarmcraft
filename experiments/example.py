from typing import override

from swarmcraft.agent import Agent
from swarmcraft.experiment import Experiment


class ExampleExperiment(Experiment):
    """Example experiment (does not use behavior trees)
    Pay careful attention to the constructor signature! It has to look exactly like this in order for your experiments to be callable from the shell.
    """
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.num_agents = int(*args[0])

    @override
    def initialize(self):
        for i in range(self.num_agents):
            self.pooler.create_bot()
        for i in range(self.num_agents):
            a = Agent(self.pooler, self.message_server, f'agent_{i}')
            a.reset()
            self.agents.append(a)

    @override
    def run(self):
        for a in self.agents:
            a.actuation.say(f'My username is {a.sensing.get_username()}, and my identifier is {a.id}')

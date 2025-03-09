from typing import override

from agents.agent import GotoAgent
from server.pooler import pooler


class Experiment:
    def __init__(self):
        self.agents = [] # all the agents that are currently involved in this experiment, alive or dead

    def initialize(self):
        """Reset this experiment to its initial state"""
        pass

    def run(self):
        """Run this experiment"""
        pass

    def cleanup(self):
        """Clean up after this experiment"""
        for a in self.agents:
            a.log()
            a.destroy()


class ExampleExperiment(Experiment):
    """Example experiment (does not use behavior trees)"""
    def __init__(self, num_agents):
        super().__init__()
        self.num_agents = num_agents

    @override
    def initialize(self):
        for i in range(self.num_agents):
            pooler.create_bot()
        for i in range(self.num_agents):
            a = GotoAgent(f'agent_{i}')
            a.reset()
            self.agents.append(a)

    @override
    def run(self):
        for a in self.agents:
            a.actuation.say(f'My username is {a.sensing.get_username()}, and my identifier is {a.id}')

from typing import override

from agent import GotoAgent

class Experiment:
    def __init__(self, pooler, minecraft_server, message_server):
        self.agents = [] # all the agents that are currently involved in this experiment, alive or dead
        self.pooler = pooler
        self.minecraft_server = minecraft_server
        self.message_server = message_server

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
    def __init__(self, pooler, minecraft_server, message_server, num_agents):
        super().__init__(pooler, minecraft_server, message_server)
        self.num_agents = num_agents

    @override
    def initialize(self):
        for i in range(self.num_agents):
            self.pooler.create_bot()
        for i in range(self.num_agents):
            a = GotoAgent(self.pooler, self.message_server, f'agent_{i}')
            a.reset()
            self.agents.append(a)

    @override
    def run(self):
        for a in self.agents:
            a.actuation.say(f'My username is {a.sensing.get_username()}, and my identifier is {a.id}')

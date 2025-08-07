from random import random

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode


class RandomNode(ActionNode):
    """
    Node for simulating random events
    Rolls a dice at each tick, returning 'success' or 'failure' based on the result
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        if len(args) > 0:
            self.probability = float(args[0])
        else:
            self.randomize_params()

    def randomize_params(self):
        self.probability = random()

    def tick(self) -> str:
        if random() < self.probability:
            return 'success'
        return 'failure'
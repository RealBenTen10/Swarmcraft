from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.actuation import PlaceHeldItem, StartDig, Look
from swarmcraft.btree.nodes.base import FallbackNode, SequenceNode
from swarmcraft.btree.nodes.sensing import IsDigging, IsLookingAtBlock


class Tester(Agent):
    def __init__(self, pooler, message_server, uid):
        super().__init__(pooler, message_server, uid)
        self.behavior = SequenceNode([Look(self, 0, -3.14/4), IsLookingAtBlock(self), StartDig(self), PlaceHeldItem(self)])

    def update(self):
        print(self.behavior.tick())

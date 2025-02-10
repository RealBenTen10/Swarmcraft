from typing import override

from behaviors.Examples import RandLook, MoveForward, CheckIfHurt, Say, GotoPoint
from btree.Nodes import SequenceNode
from world_interface.actuation import Actuation
from world_interface.sensing import Sensing

class Agent(object):
    def __init__(self, bot, id):
        self.bot = bot
        self.sensing = Sensing(self)
        self.actuation = Actuation(self)
        self.id = id # internal id

    def update(self):
        # tick behavior trees, etc, etc
        pass

class HeadlessChicken(Agent):
    def __init__(self, bot, internalid):
        super().__init__(bot, internalid)
        # example behavior
        self.if_hurt_run = SequenceNode([CheckIfHurt(self.sensing),
                                         MoveForward(self.actuation, self.sensing, 5),
                                         Say(self.actuation, "Ow!"),
                                         RandLook(self.actuation)])
    @override
    def update(self):
        status = self.if_hurt_run.tick()

class Goto(Agent):
    def __init__(self, bot, internalid):
        super().__init__(bot, internalid)
        self.behavior = GotoPoint(self.sensing, self.actuation, (-169, 4, 1220))

    @override
    def update(self):
        status = self.behavior.tick()

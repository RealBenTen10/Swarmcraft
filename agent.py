from behaviors.Examples import RandLook, MoveForward, CheckIfHurt, Say
from btree.Nodes import SequenceNode
from world_interface.actuation import Actuation
from world_interface.sensing import Sensing

class Agent(object):
    def __init__(self, bot):
        self.bot = bot
        self.sensing = Sensing(self)
        self.actuation = Actuation(self)

        self.if_hurt_run = SequenceNode([CheckIfHurt(self.sensing),
                                         MoveForward(self.actuation, self.sensing, 5),
                                         Say(self.actuation, "Ow!"),
                                         RandLook(self.actuation)])

    def update(self):
        status = self.if_hurt_run.tick() # do our behavior

from typing import override

from behaviors.Examples import Say, GotoPoint
from world_interface.actuation import Actuation
from world_interface.sensing import Sensing

# example agent
class Agent(object):
    def __init__(self, bot, uid):
        self.bot = bot
        self.sensing = Sensing(self)
        self.actuation = Actuation(self)
        self.id = uid # internal id

    def update(self):
        # tick behavior trees, etc, etc
        pass

    def reset(self):
        # called by the pooler when this agent is killed/removed from the simulation and placed back into the inactive pool
        pass

class Goto(Agent):
    def __init__(self, bot, internalid):
        super().__init__(bot, internalid)
        self.behavior = GotoPoint(self.sensing, self.actuation, (-169, 4, 1220))

    @override
    def update(self):
        status = self.behavior.tick()

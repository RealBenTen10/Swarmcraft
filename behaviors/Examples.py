import math
import random
from typing import override

from btree.Nodes import ActionNode, ConditionNode
from util import dist_sqr
from world_interface.actuation import Actuation
from world_interface.sensing import Sensing


# some example behaviors

# look in a random direction (not smoothed, agent head direction may not match actual look direction)
class RandLook(ActionNode):
    def __init__(self, actuation: Actuation):
        super().__init__()
        self.actuation = actuation

    @override
    def tick(self):
        self.actuation.look((random.uniform(-2.0 * math.pi, 2.0 * math.pi), 0))
        return 'success'

# move forward until you're some distance from the point you were on when this behavior was first called
class MoveForward(ActionNode):
    def __init__(self, actuation: Actuation, sensing: Sensing, distance: float):
        super().__init__()
        self.actuation = actuation
        self.sensing = sensing
        self.distance = distance
        self.origin = self.sensing.get_position()

    @override
    def tick(self):
        if dist_sqr(self.origin, self.sensing.get_position()) < self.distance:
            self.actuation.move('forward', 0.1)
            return 'running'
        else:
            self.origin = self.sensing.get_position() # reset where we were running from
            return 'success'

# check if your health isn't full
class CheckIfHurt(ConditionNode):
    def __init__(self, sensing: Sensing):
        super().__init__()
        self.sensing = sensing

    @override
    def condition(self):
        return self.sensing.get_health() != 20

# say something in the chat
class Say(ActionNode):
    def __init__(self, actuation: Actuation, message: str):
        super().__init__()
        self.actuation = actuation
        self.message = message

    def set_message(self, new_message: str):
        self.message = new_message

    @override
    def tick(self):
        self.actuation.say(self.message)
        return 'success'

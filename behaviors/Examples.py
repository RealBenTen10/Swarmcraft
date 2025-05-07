from typing import override

from swarmcraft.btree.nodes import ActionNode, ConditionNode, FallbackNode
from swarmcraft.util import dist_sqr

# some example behaviors
# say something in the ingame chat
class Say(ActionNode):
    def __init__(self, actuation, message: str):
        super().__init__()
        self.actuation = actuation
        self.message = message

    def set_message(self, new_message: str):
        self.message = new_message

    @override
    def tick(self):
        self.actuation.send(self.actuation.agent, self.message)
        return 'success'

class CheckIfAtPosition(ConditionNode):
    def __init__(self, sensing, position):
        super().__init__()
        self.sensing = sensing
        self.position = position

    @override
    def condition(self):
        return self.sensing.get_position() == self.position

class LookAtPosition(ActionNode):
    def __init__(self, actuation, position):
        super().__init__()
        self.actuation = actuation
        self.position = position

    @override
    def tick(self):
        self.actuation.look_at(self.position)
        return 'success'

class KeyDown(ActionNode):
    def __init__(self, actuation, direction):
        super().__init__()
        self.actuation = actuation
        self.direction = direction

    @override
    def tick(self):
        self.actuation.start_move(self.direction)
        return 'success'

class StopMove(ActionNode):
    def __init__(self, actuation):
        super().__init__()
        self.actuation = actuation

    @override
    def tick(self):
        self.actuation.stop()
        return 'success'

# this must receive continuous ticks in order to work
# should always be somehow backed up/followed by a call to stop all movement
class MoveToPoint(ActionNode):
    def __init__(self, sensing, actuation, goal):
        super().__init__()
        self.actuation = actuation
        self.sensing = sensing
        self.goal = goal

    @override
    def tick(self):
        if dist_sqr(self.sensing.get_position(), self.goal) <= 1:
            self.actuation.stop()
            return 'success'
        else:
            self.actuation.look_at(self.goal)
            self.actuation.start_move('forward')
            return 'running'


# do in sequence
class GotoPoint(FallbackNode):
    def __init__(self, sensing, actuation, point):
        super().__init__([CheckIfAtPosition(sensing, point), MoveToPoint(sensing, actuation, point), StopMove(actuation)])

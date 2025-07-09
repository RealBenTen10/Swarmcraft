from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft.util import add_tuples, CARDINAL_DIRS


class Forward(ActionNode):
    """
    Start moving forward
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('forward')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Back(ActionNode):
    """
    Start moving backward
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('backward')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Left(ActionNode):
    """
    Start moving left
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('left')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Right(ActionNode):
    """
    Start moving right
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('right')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Jump(ActionNode):
    """
    Start jumping
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('jump')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Sprint(ActionNode):
    """
    Toggle sprinting
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('sprint')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Sneak(ActionNode):
    """
    Toggle sneaking
    """
    def tick(self) -> str:
        self.agent.actuation.start_move('sneak')
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class Stop(ActionNode):
    """
    Stop all movement
    """
    def tick(self) -> str:
        self.agent.actuation.stop()
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class LookNorth(ActionNode):
    """
    Look north
    """
    def tick(self) -> str:
        self.agent.actuation.look((3.14/2, 0))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class LookSouth(ActionNode):
    """
    Look south
    """
    def tick(self) -> str:
        self.agent.actuation.look((-3.14/2, 0))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class LookEast(ActionNode):
    """
    Look east
    """
    def tick(self) -> str:
        self.agent.actuation.look((0, 0))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class LookWest(ActionNode):
    """
    Look west
    """
    def tick(self) -> str:
        self.agent.actuation.look((3.14, 0))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class RotateRight(ActionNode):
    """
    Change yaw by one positive tenth of 2pi
    """
    def tick(self) -> str:
        self.agent.actuation.look(add_tuples(self.agent.sensing.get_heading(), (0.628, 0)))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class RotateLeft(ActionNode):
    """
    Change yaw by one negative tenth of 2pi
    """
    def tick(self) -> str:
        self.agent.actuation.look(add_tuples(self.agent.sensing.get_heading(), (-0.628, 0)))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class RotateUp(ActionNode):
    """
    Change pitch by one negative tenth of 2pi
    """
    def tick(self) -> str:
        self.agent.actuation.look(add_tuples(self.agent.sensing.get_pitch(), (0.0, -0.628)))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class RotateDown(ActionNode):
    """
    Change pitch by one positive tenth of 2pi
    """
    def tick(self) -> str:
        self.agent.actuation.look(add_tuples(self.agent.sensing.get_pitch(), (0.0, 0.628)))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class LookUp(ActionNode):
    """
    Look up
    """
    def tick(self) -> str:
        self.agent.actuation.look((0, -3.14))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class LookDown(ActionNode):
    """
    Look down
    """
    def tick(self) -> str:
        self.agent.actuation.look((0, 3.14))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class StartDig(ActionNode):
    """
    Start digging
    """
    def tick(self) -> str:
        if self.agent.sensing.is_digging():
            return 'running'
        if self.agent.actuation.start_dig():
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class StopDig(ActionNode):
    """
    Stop digging
    """
    def tick(self) -> str:
        self.agent.actuation.stop_dig()
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot0(ActionNode):
    """
    Select hotbar slot 0
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(0)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot1(ActionNode):
    """
    Select hotbar slot 1
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(1)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot2(ActionNode):
    """
    Select hotbar slot 2
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(2)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot3(ActionNode):
    """
    Select hotbar slot 3
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(3)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot4(ActionNode):
    """
    Select hotbar slot 4
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(4)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot5(ActionNode):
    """
    Select hotbar slot 5
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(5)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot6(ActionNode):
    """
    Select hotbar slot 6
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(6)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot7(ActionNode):
    """
    Select hotbar slot 7
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(7)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class SelectSlot8(ActionNode):
    """
    Select hotbar slot 8
    """
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(8)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

# TODO node for placing block

# TODO node for sending message

# TODO node for sending chat

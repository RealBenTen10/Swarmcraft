import math
import random

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft.util import add_tuples, MOVEMENT_KEYS


class PressDir(ActionNode):
    """
    Start holding down the given movement key
    """
    def __init__(self, agent: Agent, key: str = None):
        super().__init__(agent)
        self.key = key
        if self.key is None:
            self.randomize_params()
        elif self.key not in MOVEMENT_KEYS:
            raise ValueError(f'key must be one of {MOVEMENT_KEYS}')

    def randomize_params(self):
        self.key = random.choice(MOVEMENT_KEYS)

    def tick(self) -> str:
        self.agent.actuation.start_move(self.key)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.key})'

class ReleaseDir(ActionNode):
    """
    Stop holding down the given movement key
    """
    def __init__(self, agent: Agent, key: str = None):
        super().__init__(agent)
        self.key = key
        if self.key is None:
            self.randomize_params()
        elif self.key not in MOVEMENT_KEYS:
            raise ValueError(f'key must be one of {MOVEMENT_KEYS}')

    def randomize_params(self):
        self.key = random.choice(MOVEMENT_KEYS)

    def tick(self) -> str:
        self.agent.actuation.stop_move(self.key)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.key})'

class Stop(ActionNode):
    """
    Stop all movement
    """
    def tick(self) -> str:
        self.agent.actuation.stop()
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class Look(ActionNode):
    """
    Look in a given direction
    """
    def __init__(self, agent: Agent, yaw: float = None, pitch: float = None):
        """
        @param yaw: horizontal rotation in radians. 0 is east, pi/2 is north
        @param pitch: vertical rotation in radians. 0 is flat, pi is down, -pi is up
        """
        super().__init__(agent)
        self.yaw = yaw
        self.pitch = pitch
        if self.pitch is None or self.yaw is None:
            self.randomize_params()

    def randomize_params(self):
        self.pitch = random.random() * 2 * math.pi
        self.yaw = (random.random() * 2 - 1) * math.pi

    def tick(self) -> str:
        self.agent.actuation.look((self.yaw, self.pitch))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.yaw}, {self.pitch})'

class Rotate(ActionNode):
    """
    Rotate the view by a given amount
    """
    def __init__(self, agent: Agent, yaw: float = None, pitch: float = None):
        """
        @param yaw: horizontal rotation in radians. positive is counterclockwise
        @param pitch: vertical rotation in radians. positive is down
        """
        super().__init__(agent)
        self.yaw = yaw
        self.pitch = pitch
        if self.pitch is None or self.yaw is None:
            self.randomize_params()

    def randomize_params(self):
        self.pitch = (random.random() * 2 - 1) * math.pi
        self.yaw = (random.random() * 2 - 1) * math.pi

    def tick(self) -> str:
        self.agent.actuation.look(add_tuples(self.agent.sensing.get_heading(), (self.yaw, self.pitch)))
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.yaw}, {self.pitch})'

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

class SelectSlot(ActionNode):
    """
    Select a hotbar slot
    """
    def __init__(self, agent: Agent, slot: int = None):
        super().__init__(agent)
        self.slot = slot
        if self.slot is None:
            self.randomize_params()
        elif self.slot < 0 or self.slot > 8:
            raise ValueError('Hotbar slot must be between 0 and 8')

    def randomize_params(self):
        self.slot = random.randint(0, 8)

    def tick(self) -> str:
        self.agent.actuation.select_hotbar(self.slot)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.slot})'

# TODO node for placing block

# TODO node for sending message

# TODO node for sending chat

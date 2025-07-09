import random

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft.util import MOVEMENT_KEYS


class IsDigging(ActionNode):
    """
    Check if digging a block
    """
    def tick(self) -> str:
        if self.agent.sensing.is_digging():
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class IsKeyDown(ActionNode):
    """
    Check if key pressed
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
        if self.agent.sensing.control_is_toggled(self.key):
            return 'success'
        return 'failure'


class IsHoldingItem(ActionNode):
    """
    Check if holding any item
    """
    def tick(self) -> str:
        if self.agent.sensing.get_held_item() is not None:
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class IsHoldingTool(ActionNode):
    """
    Check if holding any tool item
    Tools are distinguished by having durability values
    """
    def tick(self) -> str:
        item = self.agent.sensing.get_held_item()
        if item.maxDurability is not None:
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class IsLookingAtBlock(ActionNode):
    """
    Check if looking at any block
    """
    def tick(self) -> str:
        if self.agent.sensing.get_cursor_block() is not None:
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

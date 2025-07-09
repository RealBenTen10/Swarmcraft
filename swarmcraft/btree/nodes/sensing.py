from swarmcraft.btree.nodes.base import ActionNode


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


class IsMoving(ActionNode):
    """
    Check if any movement directions (forward, back, left, right, jump) are toggled
    """
    def tick(self) -> str:
        if self.agent.sensing.control_is_toggled('forward') or self.agent.sensing.control_is_toggled('backward') or self.agent.sensing.control_is_toggled('left') or self.agent.sensing.control_is_toggled('right') or self.agent.sensing.control_is_toggled('jump'):
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class IsSprinting(ActionNode):
    """
    Check if sprint is toggled
    """
    def tick(self) -> str:
        if self.agent.sensing.control_is_toggled('sprint'):
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


class IsSneaking(ActionNode):
    """
    Check if sneak is toggled
    """
    def tick(self) -> str:
        if self.agent.sensing.control_is_toggled('sneak'):
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'


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

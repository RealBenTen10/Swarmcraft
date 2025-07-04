"""
Manipulation library for btree based agents
Getting an idea of your surroundings, digging, placing blocks, select hotbar, current held item, etc
"""
from typing import override

from swarmcraft.agent import Agent
from swarmcraft.btree.movement import LookAtPosition
from swarmcraft.btree.nodes import ActionNode, ConditionNode, FallbackNode, SequenceNode
from swarmcraft.util import CARDINAL_DIRS, add_tuples


class Dig(ActionNode):
    def __init__(self, agent: Agent):
        """
        Start mining the block at the bot's cursor
        Ticks success if started mining, ticks running if already mining, ticks failure if block at cursor is not mineable
        """
        super().__init__()
        self.agent = agent

    @override
    def tick(self) -> str:
        if self.agent.sensing.is_digging():
            return 'running'
        if self.agent.actuation.start_dig():
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f"Dig[]()"

class StopDig(ActionNode):
    def __init__(self, agent: Agent):
        """
        Cancel the current digging action
        Always ticks success
        """
        super().__init__()
        self.agent = agent

    @override
    def tick(self) -> str:
        self.agent.actuation.stop_dig()
        return 'success'

    def __repr__(self) -> str:
        return f"StopDig[]()"

class IsDigging(ConditionNode):
    def __init__(self, agent: Agent):
        """
        Check if the bot is already mining something
        """
        super().__init__()
        self.agent = agent

    @override
    def condition(self) -> bool:
        return self.agent.sensing.is_digging()

    def __repr__(self) -> str:
        return f"IsDigging[]()"

class SelectHotbar(ActionNode):
    def __init__(self, agent: Agent, slot: int):
        """
        Select a given hotbar slot
        """
        super().__init__()
        self.agent = agent
        self.slot = slot

    @override
    def tick(self) -> str:
        self.agent.actuation.select_hotbar(self.slot)
        return 'success'

    def __repr__(self) -> str:
        return f"SelectHotbar[slot={self.slot}]()"

class IsHoldingItem(ConditionNode):
    def __init__(self, agent: Agent, item=None):
        """
        Check if you are holding the given item
        Passing None checks if holding any item
        """
        super().__init__()
        self.agent = agent
        self.item = item

    @override
    def condition(self) -> bool:
        if self.item is None:
            return self.agent.sensing.get_held_item() is not None
        else:
            # TODO typing stuff here
            return self.agent.sensing.get_held_item() == self.item

    def __repr__(self) -> str:
        return f"IsHoldingItem[item={self.item}]()"

class LookAndCheckBlockAtFeetCardinal(ActionNode):
    def __init__(self, agent: Agent, cardinal_dir: str, block_type: str):
        """
        Look at and check the type of the block at your feet, according to a cardinal direction
        cardinal_dir can be 'n', 'ne', 'nw', 's', 'se', 'sw', 'e', or 'w'
        block_type should be a non-namespaced block name, e.g. 'diamond_block'
        """
        self.agent = agent
        self.offset = CARDINAL_DIRS[cardinal_dir]
        self.block_type = block_type

    @override
    def tick(self) -> str:
        pos = add_tuples(self.agent.sensing.get_position(), self.offset)
        self.agent.actuation.look_at(pos)
        looking_at = self.agent.sensing.get_cursor_block().name
        if looking_at == self.block_type:
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f"LookAndCheckBlockAtFeetCardinal[dir={self.offset}, block_type={self.block_type}]()"

class CheckAllBlocksAtFeet(FallbackNode):
    def __init__(self, agent: Agent, block_type: str):
        """
        Check if any of the blocks at an agent's feet are of a given type.
        block_type should be a non-namespaced block name, e.g. 'diamond_block'
        """
        super().__init__([LookAndCheckBlockAtFeetCardinal(agent, direction, block_type) for direction in CARDINAL_DIRS.keys()])

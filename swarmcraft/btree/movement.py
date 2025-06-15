"""
Movement library for btree based agents
Going places, checking where you're at, etc
"""
from typing import override

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes import ActionNode, ConditionNode


class StartMove(ActionNode):
    """Start moving in a given direction (forward, back, left, right, jump, sprint, sneak)"""
    def __init__(self, agent: Agent, direction):
        super().__init__()
        self.agent = agent
        self.direction = direction

    def tick(self) -> str:
        self.agent.actuation.start_move(self.direction)
        return 'success'

class StopMove(ActionNode):
    """Stop moving in a given direction (forward, back, left, right, jump, sprint, sneak)"""
    def __init__(self, agent: Agent, direction):
        super().__init__()
        self.agent = agent
        self.direction = direction

    def tick(self) -> str:
        self.agent.actuation.stop_move(self.direction)
        return 'success'

class IsMoving(ConditionNode):
    """Check if an agent is trying to move in a given direction (forward, back, left, right, jump, sprint sneak)
    Only checks if that button is toggled, not if any movement is actually happening on the server"""
    def __init__(self, agent: Agent, direction):
        super().__init__()
        self.agent = agent
        self.direction = direction

    def condition(self) -> bool:
        return self.agent.sensing.control_is_toggled(self.direction)

class IsAtPosition(ConditionNode):
    """Check if an agent is at a given position
    The check is done with integers, so as long as you're in the same block, this evaluates to true"""
    def __init__(self, agent: Agent, position: tuple[int, int, int]):
        super().__init__()
        self.agent = agent
        self.position = position

    def condition(self) -> bool:
        return (int(x) for x in self.agent.sensing.get_position()) == self.position

class LookAtPosition(ActionNode):
    """Look at a given position"""
    def __init__(self, agent: Agent, position: tuple[float, float, float]):
        super().__init__()
        self.agent = agent
        self.position = position

    @override
    def tick(self) -> str:
        self.agent.actuation.look_at(self.position)
        return 'success'

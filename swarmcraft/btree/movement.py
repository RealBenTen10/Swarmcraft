"""
Movement library for btree based agents
Going places, checking where you're at, etc
"""
from typing import override

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes import ActionNode, ConditionNode, FallbackNode
from swarmcraft.util import dist_sqr


class StartMove(ActionNode):
    def __init__(self, agent: Agent, direction):
        """Start moving in a given direction (forward, back, left, right, jump, sprint, sneak)"""
        super().__init__()
        self.agent = agent
        self.direction = direction

    def tick(self) -> str:
        self.agent.actuation.start_move(self.direction)
        return 'success'

    def __repr__(self) -> str:
        return f"StartMove(direction={self.direction})"

class StopMove(ActionNode):
    def __init__(self, agent: Agent, direction):
        """Stop moving in a given direction (forward, back, left, right, jump, sprint, sneak, all)"""
        super().__init__()
        self.agent = agent
        self.direction = direction

    def tick(self) -> str:
        if self.direction == 'all':
            self.agent.actuation.stop()
            return 'success'
        self.agent.actuation.stop_move(self.direction)
        return 'success'

    def __repr__(self) -> str:
        return f"StopMove(direction={self.direction})"

class IsMoving(ConditionNode):
    def __init__(self, agent: Agent, direction):
        """Check if an agent is trying to move in a given direction (forward, back, left, right, jump, sprint sneak)
        Only checks if that button is toggled, not if any movement is actually happening on the server"""
        super().__init__()
        self.agent = agent
        self.direction = direction

    def condition(self) -> bool:
        return self.agent.sensing.control_is_toggled(self.direction)

    def __repr__(self) -> str:
        return f"IsMoving(direction={self.direction})"

class IsAtPosition(ConditionNode):
    def __init__(self, agent: Agent, position: tuple[float, float, float]):
        """Check if an agent is at a given position
        The check is done with integers, so as long as you're in the same block, this evaluates to true"""
        super().__init__()
        self.agent = agent
        self.position = position

    def condition(self) -> bool:
        return (int(x) for x in self.agent.sensing.get_position()) == (int(x) for x in self.position)

    def __repr__(self) -> str:
        return f"IsAtPosition(position={self.position})"

class LookAtPosition(ActionNode):
    def __init__(self, agent: Agent, position: tuple[float, float, float]):
        """Look at a given position"""
        super().__init__()
        self.agent = agent
        self.position = position

    @override
    def tick(self) -> str:
        self.agent.actuation.look_at(self.position)
        return 'success'

    def __repr__(self) -> str:
        return f"LookAtPosition(position={self.position})"

# TODO need a way to check if stuck?
# with a timeout probably
class WalkToPosition(FallbackNode):
    def __init__(self, agent: Agent, position: tuple[float, float, float]):
        class WalkToPositionInternal(ActionNode):
            def __init__(self):
                super().__init__()

            @override
            def tick(self) -> str:
                if dist_sqr(agent.sensing.get_position(), position) <= 1:
                    agent.actuation.stop()
                    return 'success'
                else:
                    agent.actuation.look_at(position)
                    agent.actuation.start_move('forward')
                    return 'running'

        super().__init__([IsAtPosition(agent, position), WalkToPositionInternal(), StopMove(agent, 'all')])
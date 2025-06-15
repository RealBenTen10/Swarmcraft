"""
Manipulation library for btree based agents
Getting an idea of your surroundings, digging, placing blocks, etc
"""
from typing import override

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes import ActionNode, ConditionNode


class Say(ActionNode):
    """
    Sends a given string in the game chat.
    For more powerful messaging, see btree.messaging
    """
    def __init__(self, agent: Agent, message: str):
        super().__init__()
        self.agent = agent
        self.message = message

    @override
    def tick(self) -> str:
        self.agent.actuation.say(self.message)
        return 'success'

class StartDig(ActionNode):
    """
    Start mining the block at the bot's cursor
    Ticks success if started mining, ticks failure if already mining or block at cursor is not mineable
    """
    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent

    @override
    def tick(self) -> str:
        if self.agent.actuation.start_dig():
            return 'success'
        return 'failure'

class IsDigging(ConditionNode):
    """
    Check if the bot is already mining something
    """
    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent

    @override
    def condition(self) -> bool:
        return self.agent.sensing.is_digging()

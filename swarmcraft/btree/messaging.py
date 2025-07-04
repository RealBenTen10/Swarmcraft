"""
Messaging library for btree based agents
Simplifies interaction with the different message systems and the chat queue
"""
from typing import override

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes import ActionNode, ConditionNode


class SendMessage(ActionNode):
    def __init__(self, agent: Agent, message: str, target_id: str=None, dist: int=None):
        """
        Sends a message in the internal messenger
        Configurable with target, without target, with range, without range
        target_id, if present, must be the internal id of the agent this message is meant for (not username!)
        """
        super().__init__()
        self.agent = agent
        self.message = message
        self.target = target_id
        self.dist = dist

    @override
    def tick(self) -> str:
        if self.target is not None:
            if self.dist is not None:
                self.agent.actuation.send_message_ranged(self.message, self.target, self.dist)
                return 'success'
            else:
                self.agent.actuation.send_message(self.message, self.target)
                return 'success'
        else:
            if self.dist is not None:
                self.agent.actuation.send_global_message_ranged(self.message, self.dist)
                return 'success'
            else:
                self.agent.actuation.send_global_message(self.message)
                return 'success'

    def __repr__(self) -> str:
        return f"SendMessage(msg={self.message}, target={self.target}, dist={self.dist})"


class SendChat(ActionNode):
    def __init__(self, agent: Agent, message: str):
        """
        Sends a given string in the game chat.
        """
        super().__init__()
        self.agent = agent
        self.message = message

    @override
    def tick(self) -> str:
        self.agent.actuation.say(self.message)
        return 'success'

    def __repr__(self) -> str:
        return f"SendChat(message={self.message})"


class ClearMessageQueue(ActionNode):
    def __init__(self, agent: Agent):
        """
        Clears the agent's swarmcraft messaging queue
        """
        super().__init__()
        self.agent = agent

    @override
    def tick(self) -> str:
        self.agent.sensing.messages.clear()
        return 'success'

    def __repr__(self) -> str:
        return f"ClearMessageQueue()"

class ClearChatQueue(ActionNode):
    def __init__(self, agent: Agent):
        """
        Clears the agent's minecraft chat queue
        """
        super().__init__()
        self.agent = agent

    @override
    def tick(self) -> str:
        self.agent.sensing.chats.clear()
        return 'success'

    def __repr__(self) -> str:
        return f"ClearChatQueue()"

class GotMessage(ConditionNode):
    def __init__(self, agent: Agent, message_content: str=None, sender_id: str=None, privacy: bool=None):
        """
        Check if an agent has received a given swarmcraft message
        Passing None to message_content, sender_id, privacy is a wildcard
        First message from top of queue (oldest received) is matched
        """
        super().__init__()
        self.agent = agent
        self.message_content = message_content
        self.sender_id = sender_id
        self.privacy = privacy

    @override
    def condition(self) -> bool:
        for message in self.agent.sensing.messages:
            matched = True
            if self.message_content is not None:
                matched &= message.contents == self.message_content
            if self.sender_id is not None:
                matched &= message.sender_id == self.sender_id
            if self.privacy is not None:
                matched &= message.private == self.privacy
            if matched:
                return True
        return False

    def __repr__(self) -> str:
        return f"GotMessage(content={self.message_content}, sender_id={self.sender_id}, privacy={self.privacy})"

class GotChat(ConditionNode):
    def __init__(self, agent: Agent, message_content: str=None, sender_id: str=None, privacy: bool=None):
        """
        Check if an agent has received a given minecraft chat message
        Passing None to message_content, sender_id, privacy is a wildcard
        First message from top of queue (oldest received) is matched
        """
        super().__init__()
        self.agent = agent
        self.message_content = message_content
        self.sender_id = sender_id
        self.privacy = privacy

    @override
    def condition(self) -> bool:
        for message in self.agent.sensing.chats:
            matched = True
            if self.message_content is not None:
                matched &= message.contents == self.message_content
            if self.sender_id is not None:
                matched &= message.sender_id == self.sender_id
            if self.privacy is not None:
                matched &= message.private == self.privacy
            if matched:
                return True
        return False

    def __repr__(self) -> str:
        return f"GotChat(content={self.message_content}, sender_id={self.sender_id}, privacy={self.privacy})"

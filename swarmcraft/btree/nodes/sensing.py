import random

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft.util import MOVEMENT_KEYS


class IsDigging(ActionNode):
    """
    Check if digging a block
    If the agent is digging a block, returns 'success'
    Otherwise returns 'failure'
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
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.key = args[0] if len(args) > 0 else None
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

class ClearChatQueue(ActionNode):
    def __init__(self, agent: Agent):
        """
        Clear minecraft chat queue
        """
        super().__init__(agent)

    def tick(self) -> str:
        self.agent.sensing.chats.clear()
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class ClearMessageQueue(ActionNode):
    def __init__(self, agent: Agent):
        """
        Clear swarmcraft message queue
        """
        super().__init__(agent)

    def tick(self) -> str:
        self.agent.sensing.messages.clear()
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class GotMessage(ActionNode):
    def __init__(self, agent: Agent, *args):
        """
        Check if an agent has received a swarmcraft message
        Passing None to any parameter is a wildcard.
        First message from top of queue (oldest received) is matched
        No random initialization
        """
        super().__init__(agent)
        self.message_content = args[0] if len(args) > 0 else None
        self.sender_id = args[1] if len(args) > 1 else None
        self.privacy = args[2] if len(args) > 2 else None

    def tick(self) -> str:
        for message in self.agent.sensing.messages:
            matched = True
            if self.message_content is not None:
                matched &= message.contents == self.message_content
            if self.sender_id is not None:
                matched &= message.sender_id == self.sender_id
            if self.privacy is not None:
                matched &= message.privacy == self.privacy
            if matched:
                return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.message_content}, {self.sender_id}, {self.privacy})'

class GotChat(ActionNode):
    def __init__(self, agent: Agent, *args):
        """
        Check if an agent has received a minecraft chat
        Passing None to any parameter is a wildcard.
        First chat from top of queue (oldest received) is matched
        No random initialization
        """
        super().__init__(agent)
        self.message_content = args[0] if len(args) > 0 else None
        self.sender_id = args[1] if len(args) > 1 else None
        self.privacy = args[2] if len(args) > 2 else None

    def tick(self) -> str:
        for chat in self.agent.sensing.chats:
            matched = True
            if self.message_content is not None:
                matched &= chat.contents == self.message_content
            if self.sender_id is not None:
                matched &= chat.sender_id == self.sender_id
            if self.privacy is not None:
                matched &= chat.privacy == self.privacy
            if matched:
                return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.message_content}, {self.sender_id}, {self.privacy})'

import random
import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft import MovementKeys, BlockTypes


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
        elif self.key not in [el.value for el in MovementKeys]:
            raise ValueError(f'key must be one of {[el.value for el in MovementKeys]}')

    def randomize_params(self):
        self.key = random.choice([el.value for el in MovementKeys])

    def tick(self) -> str:
        if self.agent.sensing.control_is_toggled(self.key):
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.key})'

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

class SenseBlock(ActionNode):

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.color = args[0] if len(args) > 0 else ""

    def tick(self, color = "blue_wool") -> str:
        color = self.color
        # print("Looking for Color: ", color)
        radius = 2
        block_positions = []
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                if abs(x) + abs(y) <= radius:
                    if self.agent.bot.blockAt(self.agent.bot.entity.position.offset(x, 0, y))['name'] == color:
                        return 'success'
        return 'failure'


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
    Check if looking at a block
    First argument can be any minecraft block name, e.g. 'grass_block' or None for wildcard
    randomize_params() chooses one block from util.BLOCK_TYPES or None
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        if len(args) > 0:
            self.block = args[0]
        else:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([el.value for el in BlockTypes])

    def tick(self) -> str:
        if self.agent.sensing.get_cursor_block() is not None:
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class ClearChatQueue(ActionNode):
    def __init__(self, agent: Agent, *args):
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
    """
    Clear swarmcraft message queue
    """
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
        self.message_content = str(args[0]) if len(args) > 0 else None
        self.sender_id = args[1] if len(args) > 1 else None
        self.privacy = args[2] == 'True' if len(args) > 2 else None
        self.ttl = float(args[3]) if len(args) > 3 else 1 # messages live 1 second

    def tick(self) -> str:
        now = time.time()
        #print("Looking through Messages")
        for message in reversed(self.agent.sensing.messages):
            try:
                content, ts_str = message.contents.rsplit("|", 1)
                timestamp = float(ts_str)
            except Exception as e:
                print("Couldn't extract message: ", e)
                continue

            if self.ttl is not None and (now - timestamp) > self.ttl:
                # as soon as we find an expired message, the rest is also expired
                return 'failure'
            matched = True
            if self.message_content is not None:
                matched &= str(content) == self.message_content
            if self.sender_id is not None:
                matched &= message.sender_id == self.sender_id
            if self.privacy is not None:
                matched &= message.privacy == self.privacy
            if matched:
                #print("Got Content: ", content, " and ttl ", ts_str)
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
        self.privacy = args[2] == 'True' if len(args) > 2 else False

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

class HealthCheck(ActionNode):
    def __init__(self, agent: Agent, *args):
        """
        Compare an agent's health with a fixed value.
        Random initialization sets the check value to a random int between 0 and 20, and the comparison to one of: less than, less than/equal, greater than, greater than/equal, equal, not equal.
        Constructor args, if passed, are: <check value> <comparison>.
        Check value must be in range [0, 20].
        Comparison can be one of: "LT", "LEQ", "GT", "GEQ", "EQ", "NEQ".
        """
        super().__init__(agent)
        self.val = args[0] if len(args) > 0 else None
        self.comp = args[1] if len(args) > 1 else None

        if self.val is None:
            self.randomize_params()
        elif self.val < 0 or self.val > 20:
            raise ValueError('HealthCheck val must be between 0 and 20')

        if self.comp is None:
            self.randomize_params()
        elif self.comp not in ['LT', 'LEQ', 'GT', 'GEQ', 'EQ', 'NEQ']:
            raise ValueError('HealthCheck comparison must be one of "LT", "LEQ", "GT", "GEQ", "EQ", "NEQ"')

    def randomize_params(self):
        self.val = random.randint(0, 20)
        self.comp = random.choice(['LT', 'LEQ', 'GT', 'GEQ', 'EQ', 'NEQ'])

    def tick(self) -> str:
        h = self.agent.sensing.get_health()
        if self.comp == 'LT':
            if h < self.val:
                return 'success'
            return 'failure'
        elif self.comp == 'LEQ':
            if h <= self.val:
                return 'success'
            return 'failure'
        elif self.comp == 'GT':
            if h > self.val:
                return 'success'
            return 'failure'
        elif self.comp == 'GEQ':
            if h >= self.val:
                return 'success'
            return 'failure'
        elif self.comp == 'NEQ':
            if h != self.val:
                return 'success'
            return 'failure'
        if h == self.val:
            return 'success'
        return 'failure'

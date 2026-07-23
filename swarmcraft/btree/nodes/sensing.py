import random
import time
import math

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
    """
    Sense blocks nearby
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.color = args[0] if len(args) > 0 else ""

    def tick(self, color = "blue_wool", radius = 1) -> str:
        color = self.color
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                if abs(x) + abs(y) <= radius:
                    if self.agent.bot.blockAt(self.agent.bot.entity.position.offset(x, 0, y))['name'] == color:
                        return 'success'
        return 'failure'


class SenseBlockFront(ActionNode):
    """
    Checks if the block directly in front of the agent matches block_type.
    @param args[0] block_type: Block ID/name to check (default: "blue_wool").
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.block_type = str(args[0]) if len(args) > 0 and args[0] else "blue_wool"

    def tick(self) -> str:
        yaw, _ = self.agent.actuation.heading()

        # Calculate forward offset
        dx = -math.sin(yaw)
        dz = math.cos(yaw)

        off_x = int(round(dx))
        off_z = int(round(dz))

        target_pos = self.agent.bot.entity.position.offset(off_x, 0, off_z)
        block = self.agent.bot.blockAt(target_pos)

        if block is not None and getattr(block, "name", None) == self.block_type:
            return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.block_type})'


class SenseBlockBack(ActionNode):
    """
    Checks if the block directly behind the agent matches block_type.
    @param args[0] block_type: Block ID/name to check (default: "blue_wool").
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.block_type = str(args[0]) if len(args) > 0 and args[0] else "blue_wool"

    def tick(self) -> str:
        yaw, _ = self.agent.actuation.heading()

        # Calculate backward offset
        dx = math.sin(yaw)
        dz = -math.cos(yaw)

        off_x = int(round(dx))
        off_z = int(round(dz))

        target_pos = self.agent.bot.entity.position.offset(off_x, 0, off_z)
        block = self.agent.bot.blockAt(target_pos)

        if block is not None and getattr(block, "name", None) == self.block_type:
            return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.block_type})'


class SenseBlockLeft(ActionNode):
    """
    Checks if the block directly to the left of the agent matches block_type.
    @param args[0] block_type: Block ID/name to check (default: "blue_wool").
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.block_type = str(args[0]) if len(args) > 0 and args[0] else "blue_wool"

    def tick(self) -> str:
        yaw, _ = self.agent.actuation.heading()

        # Calculate left offset (90 degrees counter-clockwise)
        dx = math.cos(yaw)
        dz = math.sin(yaw)

        off_x = int(round(dx))
        off_z = int(round(dz))

        target_pos = self.agent.bot.entity.position.offset(off_x, 0, off_z)
        block = self.agent.bot.blockAt(target_pos)

        if block is not None and getattr(block, "name", None) == self.block_type:
            return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.block_type})'


class SenseBlockRight(ActionNode):
    """
    Checks if the block directly to the right of the agent matches block_type.
    @param args[0] block_type: Block ID/name to check (default: "blue_wool").
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.block_type = str(args[0]) if len(args) > 0 and args[0] else "blue_wool"

    def tick(self) -> str:
        yaw, _ = self.agent.actuation.heading()

        # Calculate right offset (90 degrees clockwise)
        dx = -math.cos(yaw)
        dz = -math.sin(yaw)

        off_x = int(round(dx))
        off_z = int(round(dz))

        target_pos = self.agent.bot.entity.position.offset(off_x, 0, off_z)
        block = self.agent.bot.blockAt(target_pos)

        if block is not None and getattr(block, "name", None) == self.block_type:
            return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.block_type})'


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
    """
    Check if an agent has received a swarmcraft message
    Passing None to any parameter is a wildcard.
    First message from top of queue (oldest received) is matched
    No random initialization
    """
    def __init__(self, agent: Agent, *args):
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
    """
    Check if an agent has received a minecraft chat
    Passing None to any parameter is a wildcard.
    First chat from top of queue (oldest received) is matched
    No random initialization
    """
    def __init__(self, agent: Agent, *args):
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

class SenseNearestBlock(ActionNode):

    def __init__(self, agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else "blue_wool"

    def tick(self):

        if self.agent.sensing.get_nearest_block(self.block):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"

class SenseBlockInFront(ActionNode):

    def __init__(self, agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None

    def tick(self):

        block = self.agent.sensing.get_block_in_front()

        if block is None:
            return "failure"

        if self.block is None:
            return "success"

        return (
            "success"
            if block["name"] == self.block
            else "failure"
        )

class InventoryCount(ActionNode):

    def __init__(self, agent, *args):
        super().__init__(agent)

        self.item = args[0]
        self.threshold = int(args[1])

    def tick(self):

        count = self.agent.sensing.get_inventory_count(
            self.item
        )

        if count >= self.threshold:
            return "success"

        return "failure"


class IsFacingBlock(ActionNode):

    def __init__(self, agent, *args):
        super().__init__(agent)

        self.block = args[0]

    def tick(self):

        block = self.agent.sensing.get_block_in_front()

        if block is None:
            return "failure"

        if block["name"] == self.block:
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"


import random

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft import BlockTypes


class HasBlockNearby(ActionNode):
    """
    Check whether a block of a given type exists nearby.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None
        self.max_distance = int(args[1]) if len(args) > 1 else 8

        if self.block is None:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([el.value for el in BlockTypes])

    def tick(self):
        if self.agent.sensing.has_block_nearby(self.block, self.max_distance):
            return "success"
        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block}, {self.max_distance})"


class IsNearBlock(ActionNode):
    """
    Check whether the agent is close to a block.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None
        self.distance = int(args[1]) if len(args) > 1 else 2

        if self.block is None:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([el.value for el in BlockTypes])

    def tick(self):
        if self.agent.sensing.is_near_block(self.block, self.distance):
            return "success"
        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block}, {self.distance})"


class CanSeeBlockType(ActionNode):
    """
    Check if a given block type is visible.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None

        if self.block is None:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([el.value for el in BlockTypes])

    def tick(self):
        if self.agent.sensing.can_see_block_type(self.block):
            return "success"
        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"


class IsCursorOnBlock(ActionNode):
    """
    Check if the cursor currently points at any block.
    """

    def tick(self):

        if self.agent.sensing.get_cursor_block() is not None:
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}()"


class BlockAheadIs(ActionNode):
    """
    Check whether the block directly ahead matches a type.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None

        if self.block is None:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([el.value for el in BlockTypes])

    def tick(self):

        name = self.agent.sensing.get_front_block_name()

        if name == self.block:
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"


class IsStructureBlockAhead(ActionNode):
    """
    Check whether the block in front belongs to the current structure.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None

        if self.block is None:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([
            BlockTypes.BLUE_WOOL.value,
            BlockTypes.ORANGE_WOOL.value
        ])

    def tick(self):

        if self.agent.sensing.is_structure_block(self.block):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"


class InventoryContains(ActionNode):
    """
    Check if the inventory contains a specific item.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.item = args[0] if len(args) > 0 else None

    def tick(self):

        if self.agent.sensing.inventory_contains(self.item):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.item})"


class IsHoldingSpecificItem(ActionNode):
    """
    Check whether the held item matches the given item.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.item = args[0] if len(args) > 0 else None

    def tick(self):

        if self.agent.sensing.is_holding_item_name(self.item):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.item})"


class IsHoldingBlock(ActionNode):
    """
    Check whether the currently held item is a block.
    """

    def tick(self):

        if self.agent.sensing.is_holding_block():
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}()"


class HasPathToBlock(ActionNode):
    """
    Checks whether a target block exists that could be navigated to.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.block = args[0] if len(args) > 0 else None

        if self.block is None:
            self.randomize_params()

    def randomize_params(self):
        self.block = random.choice([el.value for el in BlockTypes])

    def tick(self):

        if self.agent.sensing.is_path_possible(self.block):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"


class SelectedSlotIs(ActionNode):
    """
    Check whether the currently selected hotbar slot matches.
    """

    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.slot = int(args[0]) if len(args) > 0 else random.randint(0, 8)

    def tick(self):

        if self.agent.sensing.get_selected_slot() == self.slot:
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.slot})"
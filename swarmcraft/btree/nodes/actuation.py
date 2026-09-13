import math
import random
import string
import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode, AsyncActionNode
from swarmcraft.util import add_tuples
from swarmcraft import MovementKeys
from swarmcraft import BlockTypes



class PressDir(ActionNode):
    """
    Start holding down the given movement key
    args[0] is key
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.key = args[0] if len(args) > 0 else "forward"
        if self.key is None:
            self.randomize_params()
        elif self.key not in [el.value for el in MovementKeys]:
            raise ValueError(f'key must be one of {[el.value for el in MovementKeys]}')

    def randomize_params(self):
        self.key = random.choice([el.value for el in MovementKeys])

    def tick(self) -> str:
        #print(f"Moving {self.key}")
        try:
            self.agent.actuation.start_move(self.key)
            return 'success'
        except Exception as e:
            print("Error while starting movement: ", e)
            self.agent.actuation.start_move(self.key)
            return 'success'
    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.key})'

class ReleaseDir(ActionNode):
    """
    Stop holding down the given movement key
    args[0] is key
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.key = args[0] if len(args) > 0 else "forward"
        if self.key is None:
            self.randomize_params()
        elif self.key not in [el.value for el in MovementKeys]:
            raise ValueError(f'key must be one of {[el.value for el in MovementKeys]} (was {self.key})')

    def randomize_params(self):
        self.key = random.choice([el.value for el in MovementKeys])

    def tick(self) -> str:
        self.agent.actuation.stop_move(self.key)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.key})'

class Stop(ActionNode):
    """
    Stop all movement
    """
    def tick(self) -> str:
        try:
            self.agent.actuation.stop()
            return 'success'
        except Exception as e:
            print("Failed to stop movement: ", e)
            self.agent.actuation.stop()
            return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class Look(ActionNode):
    """
    Look in a given direction
    Pass -1 to any parameter to randomize at each tick call
    """
    def __init__(self, agent: Agent, *args):
        """
        @param args[0] yaw: horizontal rotation in radians. 0 is east, pi/2 is north
        @param args[1] pitch: vertical rotation in radians. 0 is flat, pi/2 is up, - pi/2 is down
        """
        super().__init__(agent)
        self.yaw = float(args[0]) if len(args) > 0 else -1
        self.pitch = float(args[1]) if len(args) > 1 else 0
        if self.pitch is None or self.yaw is None:
            self.randomize_params()

    def randomize_params(self):
        self.pitch = random.random() * 2 * math.pi
        self.yaw = (random.random() * 2 - 1) * math.pi

    def tick(self) -> str:
        randpitch = False
        randyaw = False
        if self.pitch == -1:
            self.pitch = random.random() * 2 * math.pi
            randpitch = True
        if self.yaw == -1:
            self.yaw = (random.random() * 2 - 1) * math.pi
            randyaw = True
        self.agent.actuation.look((self.yaw, self.pitch))
        if randpitch:
            self.pitch = -1
        if randyaw:
            self.yaw = -1
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.yaw}, {self.pitch})'


import math
import random
from swarmcraft.btree.nodes.base import ActionNode
from swarmcraft.util import add_tuples


class Rotate(ActionNode):
    """
    Rotate the view by 90 degrees left or right.
    Pass "random" (or -1) to randomize between left (90) and right (-90) at each tick call.
    """

    def __init__(self, agent, *args):
        """
        @param args[0] yaw: "left", "right", "90", "-90", or "random"/-1
        @param args[1] pitch: vertical rotation in radians. positive is down
        """
        super().__init__(agent)

        # Parse the requested yaw rotation
        yaw_input = args[0] if len(args) > 0 else None

        if str(yaw_input) in ["90", "90.0", "left"]:
            self.yaw_mode = "left"
        elif str(yaw_input) in ["-90", "-90.0", "right"]:
            self.yaw_mode = "right"
        else:
            self.yaw_mode = "random"

        self.pitch = float(args[1]) if len(args) > 1 else 0.0

    def randomize_params(self):
        """Used by the GP to randomly initialize the node's parameters."""
        self.yaw_mode = random.choice(["left", "right"])

    def tick(self) -> str:
        active_mode = self.yaw_mode

        # If set to random, dynamically choose left or right for this specific tick
        if active_mode == "random":
            active_mode = random.choice(["left", "right"])

        # Convert 90 degrees to radians for Mineflayer
        # Positive is counterclockwise (left), negative is clockwise (right)
        if active_mode == "left":
            yaw_delta = math.pi / 2
        else:
            yaw_delta = -math.pi / 2

        # Fetch current heading and add the calculated rotation delta
        current_heading = self.agent.sensing.get_heading()
        target_heading = add_tuples(current_heading, (yaw_delta, self.pitch))

        self.agent.actuation.look(target_heading)

        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.yaw_mode}, {self.pitch})'

class StartDig(ActionNode):
    """
    Start digging
    If the agent is not currently digging, starts to dig and returns 'success'
    If the agent is already digging, returns 'running'
    If the agent could not start digging, returns 'failure'
    Use sensing.IsDigging to check if agent is digging or not
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.color = args[0] if len(args) > 0 else ""
    def tick(self) -> str:
        self.agent.actuation.stop()
        if self.agent.sensing.is_digging():
            return 'running'
        if self.agent.actuation.start_dig(self.color):
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class StopDig(ActionNode):
    """
    Stop digging
    """
    def tick(self) -> str:
        self.agent.actuation.stop_dig()
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class SelectSlot(ActionNode):
    """
    Select a hotbar slot
    @param args[0]: the slot to select (in range 0 to 8)
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.slot = int(args[0]) if len(args) > 0 else None
        if self.slot is None:
            self.randomize_params()
        elif self.slot < 0 or self.slot > 8:
            raise ValueError('Hotbar slot must be between 0 and 8')

    def randomize_params(self):
        self.slot = random.randint(0, 8)

    def tick(self) -> str:
        self.agent.actuation.select_hotbar(self.slot)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.slot})'

class SendMessage(ActionNode):
    """
    Sends a message in the internal messenger
    Configurable with target, without target, with range, without range
    Random initialization (all parameters None) sends a random 8 bytes to everyone
    @param args[0]: message to send
    @param args[1]: target agent id
    @param args[2]: distance to target (in blocks)
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.message = args[0] if len(args) > 0 else None
        self.target_id = args[1] if len(args) > 1 else None # Broadcast if set to None?
        self.dist = float(args[2]) if len(args) > 2 else 5 # this should be 5 blocks
        if self.message is None and self.target_id is None and self.dist is None:
            self.randomize_params()

    def randomize_params(self):
        self.message = ''.join(random.choices(string.ascii_lowercase, k=8))
        self.target_id = None
        self.dist = -1

    def tick(self) -> str:
        timestamp = time.time()
        message = f"{self.message}|{timestamp}"
        #print("Sent message: ", message)
        if self.target_id is not None:
            if self.dist != -1:
                self.agent.actuation.send_message_ranged(message, self.target_id, self.dist)
                return 'success'
            else:
                self.agent.actuation.send_message(message, self.target_id)
                return 'success'
        else:
            if self.dist != -1:
                self.agent.actuation.send_global_message_ranged(message, self.dist)
                return 'success'
            else:
                self.agent.actuation.send_global_message(message)
                return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.message}, {self.target_id}, {float(self.dist)})'

class SendChat(ActionNode):
    """
    Sends a message in the game chat
    Random initialization sends a random 8 bytes
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.message = args[0] if len(args) > 0 else None
        if self.message is None:
            self.randomize_params()

    def randomize_params(self):
        self.message = ''.join(random.choices(string.ascii_lowercase, k=8))

    def tick(self) -> str:
        self.agent.actuation.say(self.message)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.message})'

class Pathfinder(ActionNode):
    """
    Navigate to given coordinate
    Can be used with communication
        one agent can send coordinates
        rest can move to coordinate sent
    """
    def __init__(self, agent: Agent, *args):
        """
        @param args[0] yaw: horizontal rotation in radians. 0 is east, pi/2 is north
        @param args[1] pitch: vertical rotation in radians. 0 is flat, pi/2 is up, - pi/2 is down
        """
        super().__init__(agent)
        self.goal = float(args[0]) if len(args) > 0 else -1

    def tick(self) -> str:
        goal = self.agent.bot.entity.position.offset(2, 0, 2)
        print(goal)
        self.agent.actuation.navigate_to_coordinate(goal, range_goal=1)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.goal})'

class PlaceHeldItem(AsyncActionNode):
    """
    Try to place the item in your hand at the block you're currently looking at.
    If placeable, item will be placed on the face of the block your cursor is on.
    If not placeable or blocked, node fails.
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

    def do_async(self):
        if self.agent.actuation.place_block():
            self.thread_status = 'success'
        else:
            self.thread_status = 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'

class NavigateToBlock(ActionNode):
    """
    """
    def __init__(self, agent, *args):
        super().__init__(agent)

        self.block = args[0]

    def tick(self):

        if self.agent.actuation.navigate_to_block(
                self.block):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"

class FaceNearestBlock(ActionNode):
    """
    Face nearest block to agent - turn in that direction
    """
    def __init__(self, agent, *args):
        super().__init__(agent)

        self.block = args[0]

    def tick(self):

        pos = self.agent.sensing.get_nearest_block(
            self.block
        )

        if pos is None:
            return "failure"

        self.agent.actuation.face_position(
            pos.x,
            pos.y,
            pos.z
        )

        return "success"

class EquipItem(ActionNode):

    def __init__(self, agent, *args):
        super().__init__(agent)

        self.item = args[0]

    def tick(self):

        if self.agent.actuation.equip_item(
                self.item):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.item})"

class PlaceForward(ActionNode):
    """
    Action Node to place a block directly in front of the agent.
    Checks:
    1. Front block space is empty ('air').
    2. Agent has a placeable block in inventory.
    """
    def __init__(self, agent, *args):
        super().__init__(agent)

    def tick(self) -> str:
        # Step 1: Check if space in front is loaded and is "air"
        block_in_front = self.agent.sensing.get_block_in_front()
        if block_in_front is None or block_in_front.name != "air":
            return "failure"

        # Step 2: Check if agent has a block in inventory to place
        if not self.agent.sensing.has_placeable_block():
            return "failure"

        # Step 3: Place block
        if self.agent.actuation.place_block_in_front():
            return "success"

        return "failure"

    def __repr__(self) -> str:
        return f"{__class__.__name__}()"


class FaceBlockType(ActionNode):

    def __init__(self, agent, *args):
        super().__init__(agent)

        self.block = args[0]

    def tick(self):

        pos = self.agent.sensing.get_nearest_block(
            self.block
        )

        if pos is None:
            return "failure"

        if self.agent.actuation.face_position(
            pos.x,
            pos.y,
            pos.z
        ):
            return "success"

        return "failure"

    def __repr__(self):
        return f"{__class__.__name__}({self.block})"


class NavigateOneBlock(ActionNode):
    """
    Navigates exactly one block in a specified direction relative to the agent's heading.
    Only executes the movement if the target destination block is 'air'.
    @param args[0] direction: String representing direction ('front', 'left', 'right', or 'random')
    """

    def __init__(self, agent, *args):
        super().__init__(agent)

        # Parse the requested direction
        self.direction = str(args[0]).lower() if len(args) > 0 else None

        # Fallback to randomizing if missing or invalid
        if self.direction not in ["front", "left", "right", "random"]:
            self.direction = "random"

    def randomize_params(self):
        """Randomly assign one of the valid directions."""
        return random.choice(["front", "left", "right"])

    def tick(self) -> str:
        pos = self.agent.actuation.current_position()
        yaw, _ = self.agent.actuation.heading()

        if self.direction == "random":
            direction = self.randomize_params()
        else:
            direction = self.direction

        if direction == "front":
            # Forward vector
            dx = -math.sin(yaw)
            dz = math.cos(yaw)

        elif direction == "left":
            # Left vector (90 degrees counter-clockwise)
            dx = math.cos(yaw)
            dz = math.sin(yaw)

        elif direction == "right":
            # Right vector (90 degrees clockwise)
            dx = -math.cos(yaw)
            dz = -math.sin(yaw)

        else:
            return 'failure'

        # Form the absolute target coordinate
        target = (pos[0] + dx, pos[1], pos[2] + dz)

        # --- NEW: Check if the position (goal) is free ---
        # Convert our tuple coordinate to a Mineflayer Vec3 object
        target_vec = self.agent.actuation._to_vec3(target)

        # Look up the block data at the target coordinate
        target_block = self.agent.bot.blockAt(target_vec)

        # If the block is loaded in memory and it is NOT "air", cancel movement
        if target_block is not None and target_block.name != "air":
            return 'failure'
        # -------------------------------------------------

        # Pass the verified coordinate to the pathfinder
        if self.agent.actuation.move_to_position(target, range_goal=0):
            return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.direction})'


class NavigateToColor(ActionNode):
    """
    Finds a specific type of block (e.g., 'blue_wool') and navigates to it.
    """
    def __init__(self, agent, *args):
        super().__init__(agent)
        # Default to blue_wool if no argument is passed
        self.block_name = args[0] if len(args) > 0 else BlockTypes.BLUE_WOOL.value

    def tick(self) -> str:
        # Uses the pathfinder to move to the closest matching block within a 6 block radius
        if self.agent.actuation.move_to_nearest_block(self.block_name, max_distance=6, range_goal=1):
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.block_name})'


class CheckInventoryContains(ActionNode):
    """
    Returns success if the specified item is in the agent's inventory.
    @param args[0] item_name: The item to check for (e.g., 'blue_wool').
    """

    def __init__(self, agent, *args):
        super().__init__(agent)
        self.item_name = str(args[0]) if len(args) > 0 else 'blue_wool'

    def tick(self) -> str:
        if self.agent.actuation.inventory_contains(self.item_name):
            return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.item_name})'


class BroadcastLocation(ActionNode):
    """
    Broadcasts the agent's current coordinate and a custom message to the swarm.
    @param args[0] message_prefix: Prefix for the broadcast (e.g., 'FOUND_WOOL').
    @param args[1] range: Broadcast distance (-1 for global).
    """

    def __init__(self, agent, *args):
        super().__init__(agent)
        self.message_prefix = str(args[0]) if len(args) > 0 else 0 # 0 or 1 possible
        self.broadcast_range = float(args[1]) if len(args) > 1 else 5

    def tick(self) -> str:
        timestamp = time.time()
        pos = self.agent.actuation.current_position()
        sender = self.agent.id
        # Format the message as "PREFIX|x,y,z|sender|time"
        formatted_message = f"{self.message_prefix}|{pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f}|{sender}|{timestamp}"

        if self.broadcast_range < 0:
            self.agent.actuation.send_global_message(formatted_message)
        else:
            self.agent.actuation.send_global_message_ranged(formatted_message, self.broadcast_range)
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.message_prefix}, {self.broadcast_range})'


class MoveToReceivedCoordinate(ActionNode):
    """
    Parses received swarm messages and navigates to the broadcasted coordinate.
    Matches the format produced by BroadcastLocation: "PREFIX|X,Y,Z|SENDER|TIMESTAMP".

    @param args[0] target_prefix: Prefix filter to match (e.g., '0', '1', or None for any).
    @param args[1] ttl: Message expiration time in seconds (default: 5.0).
    @param args[2] range_goal: Pathfinder tolerance radius in blocks (default: 1.0).
    """

    def __init__(self, agent, *args):
        super().__init__(agent)
        self.target_prefix = str(args[0]) if len(args) > 0 and args[0] is not None else None
        self.ttl = float(args[1]) if len(args) > 1 else 5.0
        self.range_goal = float(args[2]) if len(args) > 2 else 1.0

    def tick(self) -> str:
        now = time.time()

        # Iterate from newest to oldest message
        for message in reversed(self.agent.sensing.messages):
            try:
                # Extract timestamp: "PREFIX|X,Y,Z" and "TIMESTAMP"
                content_, ts_str = message.contents.rsplit("|", 1)
                timestamp = float(ts_str)
                content, sender = content_.rsplit("|", 1)

                # Skip message if sender == receiver
                if sender == self.agent.id:
                    continue
            except Exception:
                continue

            # Check message expiration
            if self.ttl is not None and (now - timestamp) > self.ttl:
                # Since messages are chronologically ordered, older messages are also expired
                break

            # Separate prefix from coordinates: "PREFIX" and "X,Y,Z"
            try:
                prefix, coords_str = content.rsplit("|", 1)
            except ValueError:
                continue

            # Filter by matching prefix (if target_prefix is set)
            if self.target_prefix is not None and prefix != self.target_prefix:
                continue

            try:
                coords = [float(c) for c in coords_str.split(",")]
                if len(coords) != 3:
                    continue
                target_pos = (coords[0], coords[1], coords[2])
            except ValueError:
                continue
            # Move to the extracted location
            if self.agent.actuation.move_to_position(target_pos, range_goal=self.range_goal):
                # Remove the consumed message from the sensing array
                if message in self.agent.sensing.messages:
                    self.agent.sensing.messages.remove(message)

                return 'success'

        return 'failure'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.target_prefix}, {self.ttl}, {self.range_goal})'


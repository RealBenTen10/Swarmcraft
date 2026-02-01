import math
import random
import string
import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode, AsyncActionNode
from swarmcraft.util import add_tuples
from swarmcraft import MovementKeys


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

class Rotate(ActionNode):
    """
    Rotate the view by a given amount
    Pass -1 to any parameter to randomize at each tick call
    """
    def __init__(self, agent: Agent, *args):
        """
        @param args[0] yaw: horizontal rotation in radians. positive is counterclockwise
        @param args[1] pitch: vertical rotation in radians. positive is down
        """
        super().__init__(agent)
        self.yaw = float(args[0]) if len(args) > 0 else None
        self.pitch = float(args[1]) if len(args) > 1 else None
        if self.pitch is None or self.yaw is None:
            self.randomize_params()

    def randomize_params(self):
        self.pitch = (random.random() * 2 - 1) * math.pi
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
        self.agent.actuation.look(add_tuples(self.agent.sensing.get_heading(), (self.yaw, self.pitch)))
        if randpitch:
            self.pitch = -1
        if randyaw:
            self.yaw = -1
        return 'success'

    def __repr__(self) -> str:
        return f'{__class__.__name__}({self.yaw}, {self.pitch})'

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
    def __init__(self, agent: Agent, *args):
        """
        Sends a message in the internal messenger
        Configurable with target, without target, with range, without range
        Random initialization (all parameters None) sends a random 8 bytes to everyone
        @param args[0]: message to send
        @param args[1]: target agent id
        @param args[2]: distance to target (in blocks)
        """
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
        print("Sent message: ", message)
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
    def __init__(self, agent: Agent, *args):
        """
        Sends a message in the game chat
        Random initialization sends a random 8 bytes
        """
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

"""class BreakBlockAtCursor(AsyncActionNode):
    def __init__(self, agent: Agent):
        super().__init__(agent)

    def do_async(self):
        # if we can't break the block, fail
        if not self.agent.sensing.can_dig_cursor_block():
            self.thread_status = 'failure'
            return

        # otherwise start digging the block at the cursor
        self.agent.actuation.start_dig()
        # wait until we're done digging
        while self.agent.sensing.is_digging():
            pass
        # when we're done, look at the dig result
        if self.agent.sensing.finished_digging():
            # if we were able to finish the dig, we were successful
            self.thread_status = 'success'
            return
        # otherwise we weren't
        self.thread_status = 'failure'
        return

    def __repr__(self) -> str:
        return f'{__class__.__name__}()'"""

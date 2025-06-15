"""
agent actuation class
like a robot actuator suite - every agent gets one of these
"""
from javascript import require

Vec3 = require('vec3').Vec3

MOVE_DIRS = ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']

class Actuation(object):
    def __init__(self, agent):
        # agent parts
        self.agent = agent

    # send a chat message to everyone
    def say(self, message: str):
        self.agent.bot.chat(message)

    # send a chat message to one player, regardless of distance
    # this method should be avoided!
    def whisper(self, message: str, recipient_name: str):
        self.agent.bot.whisper(recipient_name, message)

    # chat methods using the pooler's chat - not rate-limited like the server
    def send_message(self, message: str, recipient_id: str):
        self.agent.message_server.send(self.agent, message, recipient_id)

    def send_message_ranged(self, message: str, recipient_id: str, distance: float):
        if distance < 0.0:
            raise ValueError('distance must be positive')
        self.agent.message_server.send(self.agent, message, recipient_id, distance)

    def send_global_message(self, message: str):
        self.agent.message_server.send(self.agent, message)

    def send_global_message_ranged(self, message: str, distance: float):
        if distance < 0.0:
            raise ValueError('distance must be positive')
        self.agent.message_server.send(self.agent, message, None, distance)

    def start_move(self, direction: str):
        """
        Start moving in a given direction (like holding down a movement key)
        Direction may be any one of ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']
        """
        if direction not in MOVE_DIRS:
            raise ValueError('direction must be one of {}'.format(MOVE_DIRS))
        self.agent.bot.setControlState(direction, True)

    def stop_move(self, direction: str):
        """
        Stop moving in a given direction (like releasing a movement key)
        Direction may be any one of ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']
        """
        if direction not in MOVE_DIRS:
            raise ValueError('direction must be one of {}'.format(MOVE_DIRS))
        self.agent.bot.setControlState(direction, False)

    def stop(self):
        """
        Stop moving in all directions
        """
        self.agent.bot.clearControlStates()

    def look_at(self, position: tuple[float, float, float]):
        """
        Look at a point
        """
        self.agent.bot.lookAt(Vec3(position[0], position[1], position[2]), True)

    def look(self, direction: tuple[float, float]):
        """
        Look in a direction
        Accepts a (yaw, pitch) tuple of radians where yaw 0 is east and pitch 0 is level/horizon
        Prefer look_at where possible - breaking/placing methods operate on the block under the cursor
        """
        self.agent.bot.look(direction[0], direction[1], True)

    def start_dig(self):
        """
        Start mining the block at the bot's cursor
        Returns false if already mining or block is not present or the block cannot be mined
        """
        if self.agent.bot.targetDigBlock is None:
            block = self.agent.bot.blockAtCursor()
            if block is not None and self.agent.bot.canDigBlock(block):
                self.agent.bot.dig(block)
                return True
        return False

    def stop_dig(self):
        """
        Stop the running digging action
        Does nothing if not digging
        """
        if self.agent.bot.targetDigBlock is not None:
            self.agent.bot.stopDigging()

    def select_hotbar(self, slot: int):
        """
        Select the given hotbar slot
        """
        if slot < 0 or slot > 8:
            raise ValueError('Hotbar slot range is 0 to 8')
        self.agent.bot.setQuickBarSlot(slot)

    def place_block(self, face: tuple[int, int, int]):
        """
        Place the currently held block
        Block will be placed at position of block under crosshair + face
        If you aren't looking at a block or aren't holding a placeable block do nothing
        Position must be any one of [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

        If the block cannot be placed (lag, position blocked by entity, etc.) this will return control as normal, but throw a JavaScriptError after 5000ms
        """
        if face not in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]:
            raise ValueError('Block face must be a unit cardinal vector such as (1, 0, 0)')
        block = self.agent.bot.blockAtCursor()
        if block is not None:
            self.agent.bot.placeBlock(block, Vec3(face[0], face[1], face[2]))

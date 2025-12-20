"""
agent actuation class
like a robot actuator suite - every agent gets one of these
"""
from javascript import require, On, Once, AsyncTask, once, off
from swarmcraft import MovementKeys

Vec3 = require('vec3').Vec3

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
            self.send_message(message, recipient_id)
        else:
            self.agent.message_server.send(self.agent, message, recipient_id, distance)

    def send_global_message(self, message: str):
        self.agent.message_server.send(self.agent, message)

    def send_global_message_ranged(self, message: str, distance: float):
        if distance < 0.0:
            self.send_global_message(message)
        else:
            self.agent.message_server.send(self.agent, message, None, distance)

    def start_move(self, direction: str):
        """
        Start moving in a given direction (like holding down a movement key)
        Direction may be any one of ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']
        """
        if direction not in [el.value for el in MovementKeys]:
            raise ValueError('direction must be one of {}'.format([el.value for el in MovementKeys]))
        self.agent.bot.setControlState(direction, True)

    def stop_move(self, direction: str):
        """
        Stop moving in a given direction (like releasing a movement key)
        Direction may be any one of ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']
        """
        if direction not in [el.value for el in MovementKeys]:
            raise ValueError('direction must be one of {}'.format([el.value for el in MovementKeys]))
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
        Accepts a (yaw, pitch) tuple of radians where yaw 0 is east, north is positive and pitch 0 is level/horizon, up is negative and down is positive
        """
        self.agent.bot.look(direction[0], direction[1], True)

    def start_dig(self):
        """
        Start mining the block at the bot's cursor
        Returns false if already mining or block is not present or the block cannot be mined
        """
        blocks_positions = self.agent.sensing.can_dig_block_in_proximity()
        async_task = False
        try:
            if async_task:
                @AsyncTask(start=True)
                def break_block(task):
                    for block in blocks_positions:
                        self.agent.bot.dig(self.agent.bot.blockAt(block))
                    self.agent.bot.chat('I started digging!')
            else:
                if len(blocks_positions) > 0:
                    print(f"{self.agent.get_uid()} in {self.agent.sensing.get_username()} starting to dig")

                    self.agent.bot.dig(self.agent.bot.blockAt(blocks_positions[0]))
                    self.agent.bot.chat('I started digging!')
            return True
        except Exception as e:
            self.agent.bot.chat(f"I had an error while digging")
            # print(f"Error during dig: {e}")
        return False

        #if self.agent.bot.targetDigBlock is None:
        #    if self.agent.sensing.can_dig_cursor_block():
        #        self.agent.bot.dig(self.agent.sensing.get_cursor_block())
        #        return True
        #return False

    def look_for_blocks(self):
        pass

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

    def place_block(self, face: tuple[int, int, int]=None):
        """
        Place the currently held block
        Block will be placed at position of block under crosshair + face
        Face must be any one of [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)], or None
        If face is None, block will be placed on the face of the block intersected by the cursor.

        If the block cannot be placed (not holding placeable item, lag, position blocked by entity, etc.) this will return false.
        If the block was placed successfully, this will return true.
        Timing is a little strange: successful placements return control immediately, failed ones take up to 5 seconds.
        Recommended to run this in its own thread.
        """
        if face is not None and face not in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]:
            raise ValueError('Block face must be a unit cardinal vector such as (1, 0, 0)')
        block = self.agent.bot.blockAtCursor()
        try:
            self.agent.bot.placeBlock(block, Vec3(face[0], face[1], face[2]) if face is not None else block.face)
            return True
        except Exception:
            return False

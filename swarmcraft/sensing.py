"""
agent sensing class
like a robot sensor suite - every agent gets one of these
"""
from collections import deque
from javascript import require, On, Once, AsyncTask, once, off
from swarmcraft.messaging import Chat
import time
Vec3 = require('vec3').Vec3
import math

class Sensing(object):
    def __init__(self, agent):
        # agent parts
        self.bot = agent.bot
        self.agent = agent

        # event queues
        self.events_queue = deque() # event queue - as asynchronous events happen on the server they are added to this queue
        self.pending_actions = [] # promises for actions which have been initialized but not yet taken

        # state queues
        self.messages = [] # messages which have been sent to you via the swarmcraft messenger
        self.chats = [] # messages which have been sent to you via minecraft chat (whisper or public)
        self.error_queue = deque()
        self.sounds_queue = deque()
        self.window_stack = deque()

        self.connected = True
        self.alive = False
        self.died = False
        self.dig_result = True

        # register all listeners for world events (which can't be accessed through bot state vars)
        # these hooks fire whenever an event happens and push the info for that event into the event queue
        # not a complete list
        @On(self.bot, "chat") # player chat
        def on_chat(this, username, message, *args):
            self.chats.append(Chat(username, self.get_username(), message, False))
        @On(self.bot, "whisper") # player whisper
        def on_whisper(this, username, message, *args): # this should push to a whisper queue
            self.chats.append(Chat(username, self.get_username(), message, True))
        # swarmcraft message queue is accessed by the messenger
        @On(self.bot, "spawn") # your spawn. probably wait for this before doing anything
        def on_spawn(this, *args):
            self.connected = True
            self.alive = True
        @On(self.bot, "death")
        def on_death(this, *args):
            self.alive = False
            self.died = True
        @On(self.bot, "end") # when you disconnect
        def on_end(this, reason, *args): # this can be a method: get_connected()
            self.connected = False
            if self.agent.bot is not None: # if your are still bound to a bot, unbind from it
                self.agent.pooler.unbind_bot(self.agent)
                print("Agent disconnected! (" + reason + ")")
        @On(self.bot, "error") # when something breaks
        def on_error(this, err, *args): # this should push to an error queue
            self.error_queue.append(("error", err))
        @On(self.bot, "soundEffectHeard") # this should push to an sfx queue
        def on_sound_effect(this, sound_name, position, volume, pitch, *args):
            self.sounds_queue.append({"soundName": sound_name, "position": position, "volume": volume, "pitch": pitch})
        @On(self.bot, "mount") # you mount a vehicle
        def on_mount(this, *args): # mount/dismount can be a method: get_mount()
            self.mount = self.bot.vehicle
        @On(self.bot, "dismount") # you dismount a vehicle
        def on_dismount(this, vehicle, *args):
            self.mount = None
        # unsure how to handle these, but does a bot really need to interact with windows?
        @On(self.bot, "windowOpen") # you are able to interact with a window (workbench, chest, etc)
        def on_windowopen(this, window, *args): # this can be a method: get_window() (get the most recently opened window)
            self.window_stack.appendleft(window)
        @On(self.bot, "windowClose") # you are no longer able to interact with a window
        def on_windowclose(this, window, *args):
            self.events_queue.append(("windowClose", window))
        @On(self.bot, "sleep")
        def on_sleep(this, *args):
            self.awake = False
        @On(self.bot, "wake")
        def on_wake(this, *args):
            self.awake = True
        @On(self.bot, "diggingCompleted")
        def on_digging_completed(this, *args):
            self.dig_result = True
        @On(self.bot, "diggingAborted")
        def on_digging_aborted(this, *args):
            self.dig_result = False

    def get_health(self):
        """
        Get the bot's health.
        """
        return self.bot.health

    def get_gameticks(self):
        """
        Get the current game time in ticks.
        Normally the game runs at 20 ticks/second.
        """
        return self.bot.time.bigTime

    def get_food(self):
        """
        Get the bot's satiation level.
        """
        return self.bot.food

    def get_username(self):
        """
        Get the bot's username.
        This is not the same as agent ID!
        """
        return self.bot.username

    def get_held_item(self):
        """
        Get the item the bot is currently holding.
        """
        # TODO what kind of thing does this return??
        return self.bot.heldItem

    def get_position(self):
        """
        Get the bot's current position.
        """
        try:
            bot_position = self.bot.entity.position
            return bot_position.x, bot_position.y, bot_position.z
        except Exception as e:
            print("Error while getting position: ", e)
            try:
                time.sleep(0.0001)
                bot_position = self.bot.entity.position
                return bot_position.x, bot_position.y, bot_position.z
            except Exception as e:
                print("Failed getting position: ", e)
            # Vec3 { x: 20.5, y: -59, z: 20.5 }

    def get_velocity(self):
        """
        Get the bot's current velocity vector.
        """
        return self.bot.entity.velocity.x, self.bot.entity.velocity.y, self.bot.entity.velocity.z

    def get_heading(self):
        """
        Get the direction the bot is looking in.
        Returns (yaw, pitch) in radians.
        """
        return self.bot.entity.yaw, self.bot.entity.pitch

    def get_ground_block(self):
        """
        Get the block the bot is standing on.
        """
        return self.bot.blockAt(self.bot.entity.position.offset(0, -1, 0))

    def can_dig_cursor_block(self):
        """
        Check if the block at the cursor is diggable and in range
        """

        return self.bot.canDigBlock(self.get_cursor_block())

    def can_dig_block_in_proximity(self):
        """
        Check the surrounding for blocks
        Is a diamond shape with side length 3
        """
        try:
            radius = 1
            block_positions = []
            for x in range(-radius, radius + 1):
                for y in range(-radius, radius + 1):
                    if abs(x) + abs(y) <= radius:
                        if self.bot.canDigBlock(self.bot.blockAt(self.bot.entity.position.offset(x, 0, y))):
                            block_positions.append(self.bot.entity.position.offset(x, 0, y))
            #print(block_positions)
            return block_positions
        except Exception as e:
            print("Can dig error: ", e)
            print("Bot of agent: ", self.bot)


    def get_cursor_entity(self):
        """
        Get the entity at the bot's cursor, to a distance of 256 blocks.
        """
        return self.bot.entityAtCursor(256)

    def is_visible(self, block):
        """
        Check if a block is visible.
        """
        return self.bot.canSeeBlock(block)

    def control_is_toggled(self, direction):
        """
        Check if the given control direction is toggled or not.
        Control directions can be forward, back, left, right, jump, sprint, or sneak
        """
        return self.bot.getControlState(direction)

    # is the bot digging a block?
    def is_digging(self):
        """
        Return true if the bot is digging a block, false otherwise.
        """
        return self.agent.bot.targetDigBlock is not None

    def finished_digging(self):
        """
        Return true if the bot successfully completed its last dig action.
        """
        return self.dig_result

    def is_alive(self):
        """
        Return true if the bot is alive.
        """
        return self.alive

    def has_died(self):
        """
        Return true if the bot has died since this method was called last
        """
        v = self.died
        self.died = False
        return v

    def pop_message(self):
        """
        Pop the last message received from the message list.
        This method also deletes the last message from the message list.
        If there are no messages in the message list, return None.
        """
        try:
            return self.messages.pop()
        except IndexError:
            return None

    def get_blocks_in_arena(self, origin, size, blocks = {'blue_wool': 4, 'orange_wool': 4, 'brown_wool': 0, 'green_wool': 0}):
        # Initialize counts for the specific blocks we care about
        block_count = {key: 0 for key in blocks}

        # We only scan the interior (avoiding the bedrock walls at index 0 and size-1)
        # Range starts at 1 and goes up to size - 1
        for x in range(1, size[0] - 1):
            for z in range(1, size[2] - 1):
                # Coordinates must match the y_pos used in set_blocks (origin[1] + 1)
                position = Vec3(origin[0] + x, origin[1] + 1, origin[2] + z)

                block = self.bot.blockAt(position)

                # Check if block exists and if it's one of our target wool types
                if block and block['name'] in block_count:
                    # We only count it if it's actually diggable (not air/bedrock)
                    block_count[block['name']] += 1

        return block_count

    def get_longest_blue_wool_line(self, origin, size, block_name = "blue_wool"):
        """
        Find the longest continuous horizontal or vertical line of blue_wool
        blocks inside the arena.

        If multiple lines have the same maximum length, all of them are returned.

        Returns:
            tuple:
                (length, lines)

            length:
                Length of the longest continuous line.

            lines:
                List of lines, where each line is a list of Vec3 positions.

            Returns (0, []) if no blue_wool line exists.
        """

        y = origin[1] + 1

        longest_length = 0
        longest_lines = []

        # ------------------------------------------------------------
        # Horizontal lines (X direction)
        # ------------------------------------------------------------
        for z in range(1, size[2] - 1):
            current_positions = []

            for x in range(1, size[0] - 1):
                position = Vec3(
                    origin[0] + x,
                    y,
                    origin[2] + z
                )

                block = self.bot.blockAt(position)

                if block is not None and block.name == block_name:
                    current_positions.append(position)
                else:
                    if len(current_positions) > longest_length:
                        longest_length = len(current_positions)
                        longest_lines = [list(current_positions)]
                    elif len(current_positions) == longest_length and longest_length > 0:
                        longest_lines.append(list(current_positions))

                    current_positions = []

            # Check line ending at the arena boundary.
            if len(current_positions) > longest_length:
                longest_length = len(current_positions)
                longest_lines = [list(current_positions)]
            elif len(current_positions) == longest_length and longest_length > 0:
                longest_lines.append(list(current_positions))

        # ------------------------------------------------------------
        # Vertical lines (Z direction)
        # ------------------------------------------------------------
        for x in range(1, size[0] - 1):
            current_positions = []

            for z in range(1, size[2] - 1):
                position = Vec3(
                    origin[0] + x,
                    y,
                    origin[2] + z
                )

                block = self.bot.blockAt(position)

                if block is not None and block.name == block_name:
                    current_positions.append(position)
                else:
                    if len(current_positions) > longest_length:
                        longest_length = len(current_positions)
                        longest_lines = [list(current_positions)]
                    elif len(current_positions) == longest_length and longest_length > 0:
                        longest_lines.append(list(current_positions))

                    current_positions = []

            # Check line ending at the arena boundary.
            if len(current_positions) > longest_length:
                longest_length = len(current_positions)
                longest_lines = [list(current_positions)]
            elif len(current_positions) == longest_length and longest_length > 0:
                longest_lines.append(list(current_positions))

        return longest_length, longest_lines

    def get_length_of_longest_line(self, origin, size, block_name="blue_wool"):
        """
                Return the current length of the longest construction line.

                The actual line-detection implementation belongs to the environment.
                """

        length, _ = self.get_longest_blue_wool_line(
            origin,
            size,
            block_name
        )

        if length is None:
            return 0

        return int(length)

    def get_distance_to_longest_blue_wool_line(self, origin, size, block_name = "blue_wool"):
        """
        Return the minimum distance from the agent to any of the longest
        continuous blue_wool lines.

        If multiple lines have the same maximum length, the closest one
        is used.

        Returns:
            float: Minimum Euclidean distance to a longest line.
            None: If no blue_wool line exists.
        """

        _, longest_lines = self.get_longest_blue_wool_line(
            origin,
            size,
            block_name
        )

        if not longest_lines:
            return None

        return min(
            self.distance_to_position(position)
            for line in longest_lines
            for position in line
        )

    # def evaluation(self, remaining_blocks, color, block_number, reward_multiplier=1, penalty_multiplier=1):
    #     evaluation = 0
    #     for block in remaining_blocks:
    #         count = block_number - remaining_blocks[block]
    #         if block == color:
    #             evaluation += count*reward_multiplier
    #         else:
    #             evaluation -= count*penalty_multiplier
    #     return evaluation

    # ------------------------------------------------------------------
    # Basic Block Queries
    # ------------------------------------------------------------------

    def get_block_at(self, position):
        """
        Returns block at world position.
        """
        return self.bot.blockAt(Vec3(position[0], position[1], position[2]))

    def get_block_relative(self, dx, dy, dz):
        """
        Returns block relative to current position.
        """
        pos = self.bot.entity.position.offset(dx, dy, dz)
        return self.bot.blockAt(pos)

    def get_block_in_front(self):
        """
        Calculates the block position directly in front of the agent
        based on current yaw and returns the Block object at that coordinate.
        """
        yaw, _ = self.agent.actuation.heading()

        # Mineflayer yaw directional offsets
        off_x = int(round(-math.sin(yaw)))
        off_z = int(round(math.cos(yaw)))

        target_pos = self.agent.bot.entity.position.offset(off_x, 0, off_z)
        return self.agent.bot.blockAt(target_pos)

    def has_placeable_block(self) -> bool:
        """
        Checks if the agent has any block item in its inventory or currently held.
        """
        registry_blocks = self.agent.bot.registry.blocksByName

        # Check currently held item first
        held = self.agent.bot.heldItem
        if held is not None and held.name in registry_blocks:
            return True

        # Search inventory for any placeable block
        for item in self.agent.bot.inventory.items():
            if item is not None and item.name in registry_blocks:
                return True

        return False

    def get_block_below(self):
        return self.bot.blockAt(self.bot.entity.position.offset(0, -1, 0))

    def get_block_above(self):
        return self.bot.blockAt(self.bot.entity.position.offset(0, 1, 0))

    # ------------------------------------------------------------------
    # Searching
    # ------------------------------------------------------------------

    def find_nearest_block(self,
                           block_name,
                           max_distance=32):
        """
        Returns nearest block matching one of block_names.
        """
        try:
            # 1. Retrieve the block data from Mineflayer's registry
            block_data = self.agent.bot.registry.blocksByName[block_name]

            if not block_data:
                print(f"Block '{block_name}' not found in registry.")
                return None

            # 2. Extract the numerical ID
            block_id = block_data.id

            # 3. Find the block using the numerical ID for the matching parameter
            block = self.agent.bot.findBlock({
                "matching": block_id,
                "maxDistance": max_distance,
                "count": 1
            })

            return block
        except Exception as e:
            print("Error while finding nearest block. Error: ", e)


    def has_block_nearby(self,
                         block_name,
                         max_distance=8):
        """
        Convenience wrapper.
        """

        return self.find_nearest_block(
            block_name,
            max_distance
        ) is not None

    # ------------------------------------------------------------------
    # Distance
    # ------------------------------------------------------------------

    def distance_to_position(self, position):
        p = self.bot.entity.position
        return math.sqrt(
            (p.x - position.x) ** 2 +
            (p.y - position.y) ** 2 +
            (p.z - position.z) ** 2
        )

    def distance_to_block(self, block):
        try:
            if block is None:
                return None

            return self.distance_to_position(block.position)
        except:
            return None

    def is_near_block(self,
                      block_name,
                      distance=2):

        block = self.find_nearest_block(
            block_name,
            distance
        )

        return block is not None

    # ------------------------------------------------------------------
    # Cursor
    # ------------------------------------------------------------------

    def get_cursor_block(self):

        try:
            return self.bot.blockAtCursor(5)
        except Exception:
            return None

    def get_cursor_face(self):
        """
        Returns face currently looked at.
        """

        block = self.bot.blockAtCursor(5)

        if block is None:
            return None

        try:
            return block.face
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Orientation
    # ------------------------------------------------------------------

    def get_yaw(self):
        return self.bot.entity.yaw

    def get_pitch(self):
        return self.bot.entity.pitch

    def get_view_direction(self):

        yaw = self.bot.entity.yaw

        return (
            -math.sin(yaw),
            0,
            -math.cos(yaw)
        )

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    def get_selected_slot(self):
        return self.bot.quickBarSlot

    def inventory_contains(self,
                           item_name):

        if self.bot.inventory is None:
            return False

        for item in self.bot.inventory.items():

            if item.name == item_name:
                return True

        return False

    def get_inventory_item(self,
                           item_name):

        if self.bot.inventory is None:
            return None

        for item in self.bot.inventory.items():

            if item.name == item_name:
                return item

        return None

    def get_inventory_item_count(self,
                           item_name):

        inventory = self.get_inventory_item(item_name)

        if inventory is None:
            return 0

        if not isinstance(inventory, dict):
            raise TypeError(
                "sensing.get_inventory() must return a dictionary."
            )
        try:
            return int(inventory.get(item_name, 0))
        except:
            print(inventory)
            print("get_inventory_item_count")
            return
    # ------------------------------------------------------------------
    # Structure Helpers
    # ------------------------------------------------------------------

    def is_structure_block(self,
                           block_names):

        block = self.get_block_in_front()

        if block is None:
            return False

        return block.name in block_names

    def get_front_block_name(self):

        block = self.get_block_in_front()

        if block is None:
            return None

        return block.name

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def can_see_block_type(self,
                           block_name,
                           max_distance=32):

        block = self.find_nearest_block(
            block_name,
            max_distance
        )

        if block is None:
            return False

        return self.bot.canSeeBlock(block)

    # ------------------------------------------------------------------
    # Navigation Helpers
    # ------------------------------------------------------------------

    def get_nearest_block_position(self,
                                   block_name,
                                   max_distance=32):

        block = self.find_nearest_block(
            block_name,
            max_distance
        )

        if block is None:
            return None

        return block.position

    def get_distance_to_next_block(self, block_name="blue_wool"):
        return self.distance_to_block(
            block = self.find_nearest_block(
            block_name,
            32
        ))

    def is_path_possible(self,
                         block_name,
                         max_distance=32):

        block = self.find_nearest_block(
            block_name,
            max_distance
        )

        return block is not None

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def is_holding_block(self):

        item = self.get_held_item()

        if item is None:
            return False

        try:
            return "block" in item.name
        except Exception:
            return False

    def is_holding_item_name(self,
                             item_name):

        item = self.get_held_item()

        if item is None:
            return False

        return item.name == item_name


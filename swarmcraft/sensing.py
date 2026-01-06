"""
agent sensing class
like a robot sensor suite - every agent gets one of these
"""
from collections import deque
from javascript import require, On, Once, AsyncTask, once, off
from swarmcraft.messaging import Chat
Vec3 = require('vec3').Vec3

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
        return self.bot.entity.position.x, self.bot.entity.position.y, self.bot.entity.position.z

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

    def get_cursor_block(self):
        """
        Get the block at the bot's cursor, to a distance of 256 blocks.
        """
        #print(self.bot.blockAtCursor(256).getProperties())

        if self.bot.canDigBlock(self.bot.blockAt(self.bot.entity.position.offset(-1,0,0))):
            print("1: ", self.bot.entity.position.offset(-1,0,0))
            print("2: ", self.bot.blockAt(self.bot.entity.position.offset(-1,0,0)))
            print("3: ", self.bot.canDigBlock(self.bot.blockAt(self.bot.entity.position.offset(-1,0,0))))
            #print("4: ", self.bot.blockAtCursor(256)) # always None
            #print("5: ", self.bot.canDigBlock(self.bot.blockAtCursor(256))) # always None
            #self.bot.canDigBlock(self.bot.blockAt(self.bot.entity.position.offset(-1,0,0)))
            try:
                @AsyncTask(start=True)
                def break_block(task):
                    self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(-1,0,0)))
                self.bot.chat('I started digging!')
            except Exception as e:
                self.bot.chat(f"I had an error while digging")
                #print(f"Error during dig: {e}")
        return self.bot.blockAtCursor(256)

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
        radius = 1
        block_positions = []
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                if abs(x) + abs(y) <= radius:
                    if self.bot.canDigBlock(self.bot.blockAt(self.bot.entity.position.offset(x, 0, y))):
                        block_positions.append(self.bot.entity.position.offset(x, 0, y))
        #print(block_positions)
        return block_positions


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

    def evaluation(self, remaining_blocks, color, block_number, reward_multiplier=1, penalty_multiplier=1):
        evaluation = 0
        for block in remaining_blocks:
            count = block_number - remaining_blocks[block]
            if block == color:
                evaluation += count*reward_multiplier
            else:
                evaluation -= count*penalty_multiplier
        return evaluation


    def old_get_blocks_in_arena_old(self, origin=(10, -60, 10), size=(100, 100, 100)):
        radius = 5
        block_positions = []
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                if abs(x) + abs(y) <= radius:
                    if self.bot.canDigBlock(self.bot.blockAt(self.bot.entity.position.offset(x, 0, y))):
                        print(self.bot.entity.position.offset(x, 0, y))
                        block_positions.append(self.bot.entity.position.offset(x, 0, y))
        print("Blocks at: ", block_positions)
        return


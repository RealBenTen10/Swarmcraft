"""
agent sensing class
like a robot sensor suite - every agent gets one of these
"""
from collections import deque
from javascript import On

from world_interface.pooler import pooler


class Sensing(object):
    def __init__(self, agent):
        # agent parts
        self.bot = agent.bot
        self.agent = agent

        # event queues
        self.events_queue = deque() # event queue - as asynchronous events happen on the server they are added to this queue
        self.pending_actions = [] # promises for actions which have been initialized but not yet taken

        # state queues
        self.chat_queue = deque()
        self.whisper_queue = deque()
        self.error_queue = deque()
        self.sounds_queue = deque()
        self.window_stack = deque()

        self.connected = True

        # register all listeners for world events (which can't be accessed through bot state vars)
        # these hooks fire whenever an event happens and push the info for that event into the event queue
        # this is not a complete list! just what i thought would be most important to have
        @On(self.bot, "chat") # player chat
        def on_chat(this, username, message, *args): # this should push to a chat queue
            self.chat_queue.append({"username": username, "message": message})
        @On(self.bot, "whisper") # player whisper
        def on_whisper(this, username, message, *args): # this should push to a whisper queue
            self.whisper_queue.append({"username": username, "message": message})
        @On(self.bot, "spawn") # your spawn. probably wait for this before doing anything
        def on_spawn(this, *args):
            self.connected = True
        @On(self.bot, "end") # when you disconnect
        def on_end(this, reason, *args): # this can be a method: get_connected()
            self.connected = False
            pooler.deactivate_agent(self.agent) # when you disconnect, also deactivate yourself
            pooler.remove_agent(self.agent) # and remove yourself from the pool
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

    def get_health(self):
        return self.bot.health

    def get_gameticks(self):
        return self.bot.time.bigTime

    def get_food(self):
        return self.bot.food

    def get_username(self):
        return self.bot.username

    def get_held_item(self):
        return self.bot.heldItem

    # state variables that you can change or that are personal to you
    # entity info
    # block you're looking at
    # entity you're looking at
    # blocks immediately around you (with findBlocks)
    # etc
    def get_position(self):
        return self.bot.entity.position.x, self.bot.entity.position.y, self.bot.entity.position.z

    def get_velocity(self):
        return self.bot.entity.velocity.x, self.bot.entity.velocity.y, self.bot.entity.velocity.z

    # yaw, pitch in radians
    def get_heading(self):
        return self.bot.entity.yaw, self.bot.entity.pitch

    # get the block the bot is standing on
    # can be an air block if the bot isn't on a block
    def get_ground_block(self):
        return self.bot.blockAt(self.bot.entity.position.offset(0, -1, 0))

    # get the block at the bot's cursor/null if no block
    def get_cursor_block(self):
        return self.bot.blockAtCursor(256)

    # get the entity at the bot's cursor/null if no entity
    def get_cursor_entity(self):
        return self.bot.entityAtCursor(256)

    # is the given block in this bot's fov?
    def is_visible(self, block):
        return self.bot.canSeeBlock(block)

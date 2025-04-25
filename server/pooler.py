"""
agent pooling class
reduces spinup time for agents by maintaining pools of active/inactive agents, and provides methods for moving agents between these pools
except for agent creation, this class does not handle agent connect/disconnect actions
agents must ask the pooler to be removed when they disconnect
"""
import operator
import time
from time import sleep
from typing import Callable, Any
from javascript import require

from server.minecraft_server import minecraft_server
import shortuuid

import util

mineflayer = require('mineflayer')

log_chat = True

WORLD_CENTER = (0, -60, 0)
pooling_location = WORLD_CENTER
connect_timeout = 5 # amount of time to wait for a bot to connect when creating a bot

class Pooler:
    def __init__(self):
        self.bound_bots = []
        self.free_bots = []

    def create_bot(self, username=None, host='localhost', port='25565'):
        """Create a bot and add it to the pool"""
        if username is None:
            username = shortuuid.ShortUUID().random(length=8)
        b = mineflayer.createBot({
            "host": host,
            "port": port,
            "username": str(username),
        })
        # wait for the bot to connect and load in
        start = time.time()
        while (b.player is None or b.entity is None) and time.time() - start < connect_timeout:
            pass
        if time.time() - start > connect_timeout:
            print("Unable to create bot (check server player limit?)")
        else:
            sleep(1) # give the bot a little time to settle - not sure if there's a better way to do this
            # this wait seems to reduce the incidence of bots not working right, but doesn't totally eliminate it
            # values below 1 are even less reliable
            # problem also seems to occur when teleporting
            self.free_bots.append(b)

    def bind_bot(self, agent):
        """Bind an agent to a bot in the pool and return true
        If there are no bots in the pool, returns false"""
        if len(self.free_bots) == 0:
            print("No free bots")
            return False
        b = self.free_bots.pop(0)
        self.reset_bot_stats(b)
        self.bound_bots.append(b)
        agent.bot = b
        return True

    def unbind_bot(self, agent):
        """Unbind an agent from its bot and return the bot to the pool"""
        b = agent.bot
        agent.bot = None # remove the bot from the agent
        self.bound_bots.remove(b)
        self.free_bots.append(b)
        self.reset_bot_control(b)
        self.reset_bot_stats(b)
        self.reset_bot_position(b)

    def reset_bot_stats(self, bot):
        minecraft_server.do(f'/clear {bot.username}') # reset bot's inventory
        minecraft_server.do(f'/effect clear {bot.username}') # clear all status effects
        minecraft_server.do(f'/effect {bot.username} instant_health 1 255') # reset bot's health
        minecraft_server.do(f'/effect {bot.username} saturation 1 255') # reset bot's hunger

    def reset_bot_position(self, bot):
        minecraft_server.do(
            f'/tp {bot.username} {pooling_location[0]} {pooling_location[1]} {pooling_location[2]}'
        )

    def reset_bot_control(self, bot):
        bot.clearControlStates()

pooler = Pooler()

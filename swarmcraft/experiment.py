from typing import override

from agent import GotoAgent
from swarmcraft.messaging import MessageServer
from swarmcraft.minecraft.server import MinecraftServer
from swarmcraft.pooler import Pooler


class Experiment:
    def __init__(self, pooler: Pooler, minecraft_server: MinecraftServer, message_server: MessageServer):
        self.agents = [] # all the agents that are currently involved in this experiment, alive or dead
        self.pooler = pooler
        self.minecraft_server = minecraft_server
        self.message_server = message_server

    def initialize(self):
        """Reset this experiment to its initial state"""
        pass

    def run(self):
        """Run this experiment"""
        pass

    def cleanup(self):
        """Clean up after this experiment"""
        for a in self.agents:
            a.log()
            a.destroy()

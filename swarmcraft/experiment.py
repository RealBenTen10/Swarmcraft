import os
from pathlib import Path
import pandas as pd

from swarmcraft.messaging import MessageServer
from swarmcraft.minecraft.server import MinecraftServer
from swarmcraft.pooler import Pooler
from swarmcraft.environment import Environment


class Experiment:
    def __init__(self, pooler: Pooler, minecraft_server: MinecraftServer, message_server: MessageServer):
        self.agents = [] # all the agents that are currently involved in this experiment, alive or dead
        self.pooler = pooler
        self.minecraft_server = minecraft_server
        self.message_server = message_server
        self.log_dir = None
        self.environment = None

    def set_log_dir(self, log_dir: Path):
        """Set the path to which this experiment saves its logs"""
        pass

    def initialize(self):
        """Reset this experiment to its initial state
        Default resets and initializes the environment, and resets all agents."""
        pass


    def log_agents(self):
        """Run the logger on all agents involved in this experiment
        Every agent gets their own logfile - no need to write identifying information like id"""
        pass

    def log_environment(self):
        """Run the logger on this experiment's environment"""
        pass

    def write_to_experiment_log(self, entry: dict):
        """Write an entry dict to this experiment's log"""
        pass

    def run(self):
        """Run this experiment
        Default does nothing"""
        pass

    def cleanup(self):
        """Clean up after this experiment
        Default destroys all agents and resets the environment"""
        pass

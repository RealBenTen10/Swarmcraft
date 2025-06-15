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
        self.environment = Environment(minecraft_server, (0, 60, 0), (25, 25, 25))
        self.pooler = pooler
        self.minecraft_server = minecraft_server
        self.message_server = message_server
        self.log_dir = None

    def set_log_dir(self, log_dir: Path):
        """Set the path to which this experiment saves its logs"""
        self.log_dir = log_dir
        os.makedirs(self.log_dir / 'agents', exist_ok=True)
        print(f'Log dir: {self.log_dir.as_posix()}')

    def initialize(self):
        """Reset this experiment to its initial state"""
        self.environment.reset()
        self.environment.initialize()
        for agent in self.agents:
            agent.reset()
        pass

    def log_agents(self, entry_id):
        """Run the logger on all agents involved in this experiment
        entry_id should be a unique identifier for the current log such as a timestamp"""
        for agent in self.agents:
            a_log = agent.log()
            a_log['entry_id'] = entry_id
            old_log_path = self.log_dir / 'agents' / f'{agent.id}.csv'
            if old_log_path.exists():
                old_log = pd.read_csv(old_log_path.absolute().as_posix())
            else:
                old_log = pd.DataFrame()
            new_log = old_log.append(a_log)
            new_log.to_csv(old_log_path.absolute().as_posix())

    def log_environment(self, entry_id):
        """Run the logger on this experiment's environment
        entry_id should be a unique identifier for the current log such as a timestamp"""
        e_log = self.environment.log()
        e_log['entry_id'] = entry_id
        old_log_path = self.log_dir / 'environment.csv'
        if old_log_path.exists():
            old_log = pd.read_csv(old_log_path.absolute().as_posix())
        else:
            old_log = pd.DataFrame()
        new_log = old_log.append(e_log)
        new_log.to_csv(old_log_path.absolute().as_posix())

    def run(self):
        """Run this experiment"""
        pass

    def cleanup(self):
        """Clean up after this experiment"""
        for a in self.agents:
            a.destroy()
        self.environment.reset()

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
        """Reset this experiment to its initial state
        Default resets and initializes the environment, and resets all agents."""
        self.environment.reset()
        self.environment.initialize()
        for agent in self.agents:
            agent.reset()
        pass

    def log_agents(self):
        """Run the logger on all agents involved in this experiment
        Every agent gets their own logfile - no need to write identifying information like id"""
        for agent in self.agents:
            a_log = agent.log() # get the agent's current log (this is a dict of scalars)
            a_log_df = pd.DataFrame([a_log]) # convert it to a df
            old_log_path = self.log_dir / 'agents' / f'{agent.id}.csv' # read their old log from disk
            if old_log_path.exists():
                old_log = pd.read_csv(old_log_path.absolute().as_posix()) # if it exists, read in
                new_log = pd.concat([old_log, a_log_df], axis=0) # concatenate new onto old along the vertical
                # we do end up with duplicate indexes
            else:
                new_log = a_log_df # if it doesn't exist, populate blank df
            new_log.to_csv(old_log_path.absolute().as_posix(), index=False) # write the new log

    def log_environment(self):
        """Run the logger on this experiment's environment"""
        e_log = self.environment.log()
        old_log_path = self.log_dir / 'environment.csv'
        if old_log_path.exists():
            old_log = pd.read_csv(old_log_path.absolute().as_posix())
        else:
            old_log = pd.DataFrame()
        new_log = pd.concat([old_log, pd.DataFrame([e_log])], axis=0)
        new_log.to_csv(old_log_path.absolute().as_posix(), index=False)

    def write_to_experiment_log(self, entry: dict):
        """Write an entry dict to this experiment's log"""
        log_path = self.log_dir / 'experiment.csv'
        if log_path.exists():
            log = pd.read_csv(log_path.absolute().as_posix())
        else:
            log = pd.DataFrame()
        new_log = pd.concat([log, pd.DataFrame([entry])])
        new_log.to_csv(log_path.absolute().as_posix(), index=False)

    def run(self):
        """Run this experiment
        Default does nothing"""
        pass

    def cleanup(self):
        """Clean up after this experiment
        Default destroys all agents and resets the environment"""
        for a in self.agents:
            a.destroy()
        self.environment.reset()

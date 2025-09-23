from copy import deepcopy
from typing import override
import time
import numpy as np

import swarmcraft.util
import swarmcraft.btree.genetics as genetics
from agents.forage import ForageAgent, SmartForageAgent
from environments.forage import ForageEnvironment
from swarmcraft.btree.nodes.misc import RandomNode, ReportPosition, ReceivePositionReport, ComparePosition
from swarmcraft.btree.nodes.actuation import PressDir, Look, Rotate, Stop
from swarmcraft.btree.nodes.sensing import HealthCheck
from swarmcraft.experiment import Experiment

ORIGIN = (10, -60, 10)
SIZE = (20, 10, 20)
START_LOCATION = (20, -55, 20)

class ForageEvolved(Experiment):
    def __init__(self, pooler, minecraft_server, message_server, *args):
        super().__init__(pooler, minecraft_server, message_server)
        self.last_update_time = None
        self.update_interval = 1. # how many seconds to wait between experiment updates
        self.reproduction_threshold = 16. # how much health an agent needs to reproduce
        self.reproduction_cost = 10. # how much it costs to reproduce
        self.start_health = 6. # how much health new agents start with
        self.decay_rate = 1 # how much health per second do agents lose?
        self.init_agent_count = int(*args[0]) if len(args) == 1 else 5
        self.run_time_sec = int(*args[1]) if len(args) == 2 else 60 * 5
        self.environment = ForageEnvironment(self.minecraft_server, ORIGIN, SIZE, 1, 1, 10)
        self.total_agents_existed = 0
        self.current_agent_count = 0

    @override
    def initialize(self):
        super().initialize()
        self.minecraft_server.send('say initialized foraging environment')

        # create twice as many bots as initial agents
        for _ in range(self.init_agent_count * 2):
            if len(self.pooler.free_bots) == 0:
                self.pooler.create_bot()
        self.minecraft_server.send('say initialized bots')

        # set up initial agents
        # make sure we have twice as many bots available as we need for the initial pop (to allow room for population growth)
        self.agents = []
        for i in range(self.init_agent_count):
            a = SmartForageAgent(self.pooler, self.message_server, f'forager_{self.total_agents_existed}', START_LOCATION, self.environment) # init agent
            genetics.generate_minmax(1, 3, a) # generate a tree for them
            self.total_agents_existed += 1
            self.current_agent_count += 1
            a.reset()
            self.agents.append(a)
            self.minecraft_server.send(f'setphealth {a.sensing.get_username()} {self.start_health}')
            print('added', i)
        self.minecraft_server.send('say initialized foraging agents')
        self.last_update_time = time.time()

        # set up the gene pool
        genetics.reset_terminals()
        # we want - agents do random walk
        # if an agent makes more than (some amount) in one update, send a position report (to agents in neighborhood)
        # agents that get a position report should head for that place
        genetics.add_terminals([
            RandomNode, # for random walk cutoff decision
            ReportPosition,
            ReceivePositionReport, # reads a received position report into instance var position_report
            ComparePosition, # given a position, the agent's current position, and a cardinal direction, this returns success/failure depending on if the difference between positions in that direction is greater than 1
            # position compared is that stored in agent instance var compare_position
            Look,
            PressDir,
            Rotate,
            Stop,
            HealthCheck
        ])


    @override
    def run(self):
        start_time = time.time()
        for a in self.agents:
            self.minecraft_server.send(f'command tp {a.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}')
        while time.time() - start_time < self.run_time_sec and self.current_agent_count > 0:
            if time.time() - self.last_update_time > self.update_interval:
                agents_not_dead = []
                for a in self.agents:
                    # think
                    a.update()

                    # apply food and damage
                    min_dist = np.inf
                    for pos in self.environment.resource_positions:
                        min_dist = min(min_dist, swarmcraft.util.dist_sqr(a.sensing.get_position(), pos))
                    bonus = (1. / max(min_dist, 0.005)) # how much bonus health? (at most 20)
                    # apply bonus
                    self.minecraft_server.send(f'changephealth {a.sensing.get_username()} {bonus}')
                    # apply damage
                    self.minecraft_server.send(f'command damage {a.sensing.get_username()} {self.decay_rate}')
                    self.minecraft_server.send(f'say {a.sensing.get_username()}: gain {bonus}, lose {self.decay_rate}')
                    # obviously it's nicer and probably a little quicker to say something like change = bonus - decay_rate
                    # but this is more accurate
                    self.minecraft_server.send(f'command say {a.sensing.get_username()}: gain {bonus}, lose {self.decay_rate}')

                    # if the agent died after damage application, remove and skip to next agent
                    if a.sensing.has_died():
                        a.actuation.stop()
                        a.reset()
                        a.destroy()
                        self.current_agent_count -= 1
                        continue

                    # reproduce with mutation if able and population cap not reached
                    if a.sensing.get_health() >= self.reproduction_threshold and len(self.pooler.free_bots) > 0:
                        child = SmartForageAgent(self.pooler, self.message_server, f'forager_{self.current_agent_count}', START_LOCATION, self.environment) # instantiate the child
                        child.tree = deepcopy(a.tree) # copy the parent's tree
                        genetics.mutate_and_rebind(child.tree, child) # mutate the child's tree, bind the child's nodes to the child
                        child.parent_uid = a.id # do parent tracking
                        child.reset() # reset child stats
                        agents_not_dead.append(child) # remember the child is alive
                        self.minecraft_server.send(f'setphealth {child.sensing.get_username()} {self.start_health}') # set child starting health
                        self.minecraft_server.send(f'command tp {child.sensing.get_username()} {START_LOCATION[0]} {START_LOCATION[1]} {START_LOCATION[2]}') # teleport into arena

                        self.minecraft_server.send(f'command damage {a.sensing.get_username()} {self.reproduction_cost}') # apply reproduction cost to parent

                        # statistics for the experiment
                        self.total_agents_existed += 1
                        self.current_agent_count += 1

                    agents_not_dead.append(a) # keep this agent alive if we made it this far

                # once all agents updated, remember the live ones
                self.agents = agents_not_dead

                # log everyone
                self.log_agents()
                self.write_to_experiment_log({'time': time.time() - start_time, 'population': self.current_agent_count}) #TODO log food source positions

                # when did this update take place?
                self.last_update_time = time.time()
import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.actuation import PressDir, Look, StartDig
from swarmcraft.btree.nodes.base import SSequenceNode, SequenceNode
from swarmcraft.btree.nodes.misc import RandomNode


class ForageAgent(Agent):
    def __init__(self, pooler, message_server, uid, start_location, env, parent_uid=None):
        super().__init__(pooler, message_server, uid)
        self.start_location = start_location
        self.env = env
        # define btree - random walk
        self.tree = SSequenceNode([
            SequenceNode([ # pick a new direction and press forward
                Look(self, -1, 0), # random yaw at each call, flat pitch
                #PressDir(self, 'forward') # press forward
                StartDig(self)
            ]),
            RandomNode(self, 0.5) # 50% chance to succeed - if succeeds, we loop back and pick a new direction to go (because this is a SSequenceNode, so state is remembered)
        ])
        self.parent_uid = parent_uid

    def update(self):
        self.tree.tick()

    def log(self):
        if self.bot is not None:
            x, y, z = self.sensing.get_position()
            health = self.sensing.get_health()
        else:
            x, y, z = (None, None, None)
            health = None
        return {
            'time': time.time(),
            'parent': str(self.parent_uid),
            'x': x,
            'y': y,
            'z': z,
            'health': health,
        }

    def reset(self):
        try:
            self.pooler.reset_bot_stats(self.bot)
            self.pooler.reset_bot_control(self.bot)
            self.pooler.reset_bot_position(self.bot)
        except Exception as e:
            #print(f"Error while reseting agent: {e}")
            pass

class SmartForageAgent(Agent):
    def __init__(self, pooler, message_server, uid, start_location, env, parent_uid=None):
        super().__init__(pooler, message_server, uid)
        self.start_location = start_location
        self.env = env
        self.parent_uid = parent_uid
        # start with a random walk btree
        self.tree = None
        # for ReceivePositionReport and ComparePosition to read into
        self.position_report = (0, 0, 0)
        self.compare_position = (0, 0, 0)

    def update(self):
        if self.tree is not None:
            self.tree.tick()
        # COPY! (not move reference) the received report into the position to compare
        self.compare_position = (self.position_report[0], self.position_report[1], self.position_report[2])

    def log(self):
        if self.bot is not None:
            x, y, z = self.sensing.get_position()
            health = self.sensing.get_health()
        else:
            x, y, z = (None, None, None)
            health = None
        return {
            'time': time.time(),
            'parent': str(self.parent_uid),
            'x': x,
            'y': y,
            'z': z,
            'health': health,
            'tree': self.tree.__repr__(),
        }
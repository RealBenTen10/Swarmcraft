import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.actuation import PressDir, Look, StartDig, ReleaseDir
from swarmcraft.btree.nodes.sensing import CanDigBlock
from swarmcraft.btree.nodes.base import SequenceNode, FallbackNode
from swarmcraft.btree.nodes.misc import RandomNode


class ForageAgent(Agent):
    def __init__(self, pooler, message_server, uid, start_location, env, parent_uid=None):
        super().__init__(pooler, message_server, uid)
        self.start_location = start_location
        self.environment = env
        # define btree - random walk
        self.tree = None
        self.parent_uid = parent_uid
        self.positions = []

    def set_tree(self, tree):
        self.tree = tree

    def update(self):
        #print("Ticking tree of ", self.get_uid(), " in ", self.sensing.get_username())
        self.movement_tracker()
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
            #self.pooler.reset_bot_stats(self.bot)
            self.pooler.reset_bot_control(self.bot)
            self.pooler.reset_bot_position(self.bot)
            # clear messages for next run
            try:
                self.sensing.messages.clear()
            except Exception as e:
                print(f"Error while resetting message queue: {e}")
        except Exception as e:
            print(f"Error while resetting agent: {e}")
            pass

    def movement_tracker(self):
        pos = self.sensing.get_position()
        rounded = tuple(round(x) for x in pos)
        if rounded not in self.positions:
            self.positions.append(rounded)

    def evaluation(
            self,
            remaining_blocks,
            color,
            initial_blocks,
            reward_multiplier=1,
            penalty_multiplier=1
    ):
        evaluation = 0
        #print("blocks: ", initial_blocks, remaining_blocks)
        for block, initial_count in initial_blocks.items():
            remaining_count = remaining_blocks.get(block, 0)
            diff = initial_count - remaining_count

            if block == color:
                evaluation += diff * reward_multiplier
            else:
                evaluation -= diff * penalty_multiplier

        evaluation += len(self.positions)*0.01
        self.positions = []
        return evaluation


import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import SequenceNode, FallbackNode
from swarmcraft.btree.nodes.actuation import StartDig, PressDir, Rotate, ReleaseDir, SendMessage, Pathfinder
from swarmcraft.btree.nodes.sensing import SenseBlock, GotMessage
from swarmcraft import BlockTypes

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
        self.tree = Pathfinder(self)
        # self.tree = SequenceNode([
        #    Rotate(self,  -1),
        #    FallbackNode([
        #        SequenceNode([
        #            SenseBlock(self, "blue_wool"),
        #            ReleaseDir(self),
        #            StartDig(self, "blue_wool")
        #        ]),
        #        PressDir(self)
        #    ])
        # ])

    def update(self):
        #print("Ticking tree of ", self.get_uid(), " in ", self.sensing.get_username())
        self.movement_tracker()
        self.tree.tick()


    def reset(self):
        try:
            self.positions = []
            #self.pooler.reset_bot_stats(self.bot)
            self.pooler.reset_bot_control(self.bot)
            self.pooler.reset_bot_position(self.bot)
            self.actuation.stop()
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
            size,
            color,
            initial_blocks,
            reward_multiplier=1,
            penalty_multiplier=1,
            unique_positions_count: int | None = None
    ):
        """
        Compute fitness contribution for a run.

        Parameters
        ----------
        remaining_blocks : dict[str, int]
            Counts of blocks currently in the arena after the run.
        color : str
            Target mission color (e.g., "blue_wool").
        initial_blocks : dict[str, int]
            Counts of blocks originally placed at the start of the run.
        reward_multiplier : float
            Reward factor for digging the correct color.
        penalty_multiplier : float
            Penalty factor for digging wrong colors.
        unique_positions_count : int | None
            If provided, use this as the exploration count (swarm aggregation).
            If None, falls back to this agent's internal self.positions length.

        Returns
        -------
        float
            Fitness value for (blocks destroyed +/-) + exploration reward.
        """
        evaluation = 0.0

        # block reward/penalty
        for block, initial_count in initial_blocks.items():
            remaining_count = remaining_blocks.get(block, 0)
            diff = initial_count - remaining_count

            if block == color:
                evaluation += diff * reward_multiplier
            else:
                evaluation -= diff * penalty_multiplier

        # exploration reward (swarm-aware)
        explored = unique_positions_count if unique_positions_count is not None else len(self.positions)
        # total possible exploration (size*size with offset for wall)
        # e.g. 18*18 = 324
        total = (size[0]-2)*(size[2]-2)
        if total <= 0:
            # should not happen
            evaluation += 1
        else:
            # add exploration bonus - gives at most +1
            evaluation += explored/total

        # do not clear here for swarm case; caller controls clearing
        # (keep this to avoid surprises if caller still uses per-agent evaluation)
        if unique_positions_count is None:
            self.positions = []

        return round(evaluation, 4)



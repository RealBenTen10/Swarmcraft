import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import SequenceNode, FallbackNode
from swarmcraft.btree.nodes.actuation import (
    StartDig, PressDir, Rotate, ReleaseDir, SendMessage,
    Pathfinder, PlaceForward, NavigateToColor, NavigateOneBlock,
    MoveToReceivedCoordinate, BroadcastLocation
)
from swarmcraft.btree.nodes.sensing import SenseBlock, GotMessage, SenseBlockFront
from swarmcraft import BlockTypes


class ConstructionAgent(Agent):
    def __init__(self, pooler, message_server, uid, start_location, env, parent_uid=None):
        super().__init__(pooler, message_server, uid)
        self.start_location = start_location
        self.environment = env
        self.tree = None
        self.parent_uid = parent_uid
        self.positions = []

    def set_tree(self, tree):
        self.tree = tree


    def update(self):
        self.movement_tracker()
        if self.tree:
            self.tree.tick()

    def reset(self):
        try:
            self.positions = []
            self.pooler.reset_bot_control(self.bot)
            self.pooler.reset_bot_position(self.bot)
            self.actuation.stop()
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

    def _compute_max_line_length(self, block_coords: set[tuple[int, int, int]]) -> int:
        """
        Calculates the maximum length of contiguous target blocks along either
        the X or Z direction on the same Y horizontal plane.
        """
        if not block_coords:
            return 0

        max_line = 0

        # Check contiguous lines along X-axis (fixed Y and Z)
        for x, y, z in block_coords:
            # Check length to the right (+X direction)
            length_x = 0
            curr_x = x
            while (curr_x, y, z) in block_coords:
                length_x += 1
                curr_x += 1
            max_line = max(max_line, length_x)

            # Check length along Z-axis (+Z direction)
            length_z = 0
            curr_z = z
            while (x, y, curr_z) in block_coords:
                length_z += 1
                curr_z += 1
            max_line = max(max_line, length_z)

        return max_line

    def evaluation(
            self,
            color="blue_wool",
            unique_positions_count: int | None = None
    ) -> float:
        """
        Compute fitness evaluation for construction performance.

        Fitness components:
        1. Primary: Maximum continuous block line length in X or Z direction on floor level.
        2. Bonus: Secondary tie-breaker for exploration (+0.0 to +1.0).
        """
        evaluation = 0.0

        origin = self.environment.origin
        size = self.environment.size
        floor_y = origin[1] + 1  # Bedrock surface level

        # 1. Retrieve all placed blocks matching target color inside the arena volume
        # Expected return format from sensing: list of Vec3/tuples [(x, y, z), ...]
        placed_blocks = self.sensing.get_blocks_in_arena(
            origin,
            size,
            target_block=color
        )

        # 2. Filter for blocks validly placed on the floor plane (no towers)
        valid_floor_blocks = {
            (int(round(b[0])), int(round(b[1])), int(round(b[2])))
            for b in placed_blocks
            if int(round(b[1])) == floor_y
        }

        # 3. Calculate max contiguous line score
        max_line = self._compute_max_line_length(valid_floor_blocks)
        evaluation += float(max_line)

        # 4. Add exploration bonus as tie-breaker (+0.0 to +1.0)
        explored = unique_positions_count if unique_positions_count is not None else len(self.positions)
        total_tiles = (size[0] - 2) * (size[2] - 2)

        if total_tiles > 0:
            evaluation += (explored / total_tiles)

        if unique_positions_count is None:
            self.positions = []

        return round(evaluation, 4)
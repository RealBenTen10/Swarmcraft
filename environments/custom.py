import random
import time
from typing import override

from swarmcraft.environment import Environment
from swarmcraft import BlockTypes


class BlocksEnvironment(Environment):
    """
    Environment for block-based swarm experiments.

    Supported scenarios:
        - "random": randomly distributed blocks
        - "empty": no initial blocks; agents place blocks themselves
        - "single_blue": one blue wool block
        - "three_blue_line": three blue wool blocks in a straight line

    The central 3x3 area is always reserved for agent spawning.
    """

    def __init__(self, minecraft_server, origin, size, scenario="random"):
        super().__init__(minecraft_server)

        self.origin = origin
        self.size = size
        self.resource_positions = []

        self.scenario = scenario

        # Block specification and fixed positions
        self.blocks = None
        self.blocks_position = None

        # Static arena structures are only built once
        self._static_built = False

    # -------------------------------------------------------------------------
    # ARENA CLEANUP
    # -------------------------------------------------------------------------

    def clean_environment(self, radius: int = 15, clear_height: int = 6):
        """
        Clear a large area around the arena.
        """

        x0 = self.origin[0] - radius
        y0 = self.origin[1]
        z0 = self.origin[2] - radius

        sx = self.size[0] + 2 * radius
        sy = clear_height
        sz = self.size[2] + 2 * radius

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} "
            f"{sx} {sy} {sz} "
            f"minecraft:{BlockTypes.AIR.value}"
        )

    def reset_arena_interior(self):
        """
        Remove all blocks from the playable interior.

        The bedrock floor, perimeter walls, stairs and roof remain untouched.
        """

        if self.size[0] < 3 or self.size[2] < 3:
            return

        x0 = self.origin[0] + 1
        y0 = self.origin[1] + 1
        z0 = self.origin[2] + 1

        sx = self.size[0] - 2
        sy = 1
        sz = self.size[2] - 2

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} "
            f"{sx} {sy} {sz} "
            f"minecraft:{BlockTypes.AIR.value}"
        )

    @override
    def reset(self):
        """
        Reset only the playable interior.
        """

        self.reset_arena_interior()

    # -------------------------------------------------------------------------
    # STATIC ARENA
    # -------------------------------------------------------------------------

    def _build_bedrock_arena(self):
        """
        Build bedrock floor and two-block-high perimeter walls.
        """

        ox, oy, oz = self.origin
        sx = self.size[0]
        sz = self.size[2]

        bedrock = f"minecraft:{BlockTypes.BEDROCK.value}"

        # Floor
        self.minecraft_server.send(
            f"setcube {ox} {oy} {oz} "
            f"{sx} 1 {sz} {bedrock}"
        )

        wall_y = oy + 1
        wall_h = 2

        # North
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz} "
            f"{sx} {wall_h} 1 {bedrock}"
        )

        # South
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz + sz - 1} "
            f"{sx} {wall_h} 1 {bedrock}"
        )

        # West
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz} "
            f"1 {wall_h} {sz} {bedrock}"
        )

        # East
        self.minecraft_server.send(
            f"setcube {ox + sx - 1} {wall_y} {oz} "
            f"1 {wall_h} {sz} {bedrock}"
        )

    def _build_observer_stairs(self):
        """
        Build observer stairs along one side of the arena.
        """

        base_y = self.origin[1]
        z_edge = self.origin[2] - 2

        stone = f"minecraft:{BlockTypes.STONE_BRICK.value}"

        for step_idx in range(5):
            height = 5 - step_idx
            z = z_edge - step_idx

            self.minecraft_server.send(
                f"setcube {self.origin[0]} {base_y} {z} "
                f"{self.size[0]} {height} 1 {stone}"
            )

        stairs_block = (
            f"minecraft:{BlockTypes.STONE_BRICK_STAIRS.value}"
            f"[facing=south,half=bottom]"
        )

        x1 = self.origin[0]
        x2 = self.origin[0] + self.size[0] - 1

        for step_idx in range(6):
            height = 6 - step_idx
            z = z_edge - step_idx + 1
            y_stairs = base_y + height

            self.minecraft_server.send(
                f"command fill {x1} {y_stairs} {z} "
                f"{x2} {y_stairs} {z} {stairs_block}"
            )

        z_ground = z_edge - 5

        self.minecraft_server.send(
            f"command fill {x1} {base_y} {z_ground} "
            f"{x2} {base_y} {z_ground} {stairs_block}"
        )

    def _build_glass_roof(self):
        """
        Build glass roof at origin.y + 5.
        """

        y = self.origin[1] + 5
        glass = f"minecraft:{BlockTypes.GLASS.value}"

        self.minecraft_server.send(
            f"setcube {self.origin[0] - 1} {y} {self.origin[2] - 1} "
            f"{self.size[0] + 2} 1 {self.size[2] + 2} {glass}"
        )

    def build_static_structures_once(self):
        """
        Build the static arena structures exactly once.
        """

        if self._static_built:
            return

        self._build_bedrock_arena()
        self._build_observer_stairs()
        self._build_glass_roof()

        self._static_built = True

    # -------------------------------------------------------------------------
    # INITIALIZATION
    # -------------------------------------------------------------------------

    @override
    def initialize(self):
        """
        Initialize the arena and prepare the selected scenario.
        """

        self.build_static_structures_once()

        # Prepare positions for scenarios that require initial blocks.
        if self.scenario == "random":
            self.shuffle_block_positions()

        elif self.scenario == "empty":
            self.blocks = {}
            self.blocks_position = {}

        elif self.scenario == "single_blue":
            self.shuffle_block_positions({
                "blue_wool": 1
            })

        elif self.scenario == "three_blue_line":
            self.create_three_blue_line()

        else:
            raise ValueError(
                f"Unknown scenario '{self.scenario}'. "
                f"Supported scenarios: "
                f"'random', 'empty', 'single_blue', 'three_blue_line'."
            )

    # -------------------------------------------------------------------------
    # CENTRAL 3x3 SPAWN AREA
    # -------------------------------------------------------------------------

    def get_spawn_area(self):
        """
        Return the coordinates belonging to the central 3x3 area.

        The 3x3 area is centered on the arena's center.

        Returns
        -------
        set[tuple[int, int, int]]
            All reserved coordinates.
        """

        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2
        y = self.origin[1] + 1

        spawn_area = set()

        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                spawn_area.add(
                    (center_x + dx, y, center_z + dz)
                )

        return spawn_area

    def is_spawn_area(self, coordinate):
        """
        Check whether a coordinate is inside the reserved central 3x3 area.
        """

        return coordinate in self.get_spawn_area()

    # -------------------------------------------------------------------------
    # RANDOM BLOCK POSITIONS
    # -------------------------------------------------------------------------

    def shuffle_block_positions(self, blocks=None):
        """
        Generate random block positions.

        The central 3x3 area is always left empty.
        """

        if blocks is None:
            blocks = {
                "blue_wool": 4,
                "orange_wool": 4,
                "brown_wool": 0,
                "green_wool": 0
            }

        self.blocks = dict(blocks)

        if self.size[0] < 5 or self.size[2] < 5:
            self.blocks_position = {
                block_type: []
                for block_type in self.blocks
            }

            return

        y_pos = self.origin[1] + 1

        spawn_area = self.get_spawn_area()

        # All valid interior coordinates
        available_positions = []

        for x_pos in range(
            self.origin[0] + 1,
            self.origin[0] + self.size[0] - 1
        ):
            for z_pos in range(
                self.origin[2] + 1,
                self.origin[2] + self.size[2] - 1
            ):
                coordinate = (x_pos, y_pos, z_pos)

                if coordinate not in spawn_area:
                    available_positions.append(coordinate)

        total_needed = sum(
            int(count)
            for count in self.blocks.values()
        )

        if total_needed > len(available_positions):
            raise ValueError(
                f"Too many blocks requested ({total_needed}) "
                f"for available capacity ({len(available_positions)}) "
                f"after reserving the central 3x3 spawn area."
            )

        random.shuffle(available_positions)

        positions = {
            block_type: []
            for block_type in self.blocks
        }

        position_index = 0

        for block_type, count in self.blocks.items():
            for _ in range(int(count)):
                positions[block_type].append(
                    available_positions[position_index]
                )

                position_index += 1

        self.blocks_position = positions

    # -------------------------------------------------------------------------
    # THREE BLUE BLOCK LINE
    # -------------------------------------------------------------------------

    def create_three_blue_line(self):
        """
        Create exactly three blue wool blocks in a straight line.

        The line can be horizontal or vertical and is guaranteed not to
        intersect the central 3x3 spawn area.
        """

        if self.size[0] < 5 or self.size[2] < 5:
            raise ValueError(
                "Arena must be at least 5x5 to place three blocks "
                "while keeping the central 3x3 area free."
            )

        y_pos = self.origin[1] + 1

        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2

        spawn_area = self.get_spawn_area()

        valid_lines = []

        # -------------------------------------------------------------
        # Horizontal lines
        # -------------------------------------------------------------

        for z_pos in range(
            self.origin[2] + 1,
            self.origin[2] + self.size[2] - 1
        ):
            for x_pos in range(
                self.origin[0] + 1,
                self.origin[0] + self.size[0] - 3
            ):
                line = [
                    (x_pos, y_pos, z_pos),
                    (x_pos + 1, y_pos, z_pos),
                    (x_pos + 2, y_pos, z_pos)
                ]

                if not any(
                    coordinate in spawn_area
                    for coordinate in line
                ):
                    valid_lines.append(line)

        # -------------------------------------------------------------
        # Vertical lines
        # -------------------------------------------------------------

        for x_pos in range(
            self.origin[0] + 1,
            self.origin[0] + self.size[0] - 1
        ):
            for z_pos in range(
                self.origin[2] + 1,
                self.origin[2] + self.size[2] - 3
            ):
                line = [
                    (x_pos, y_pos, z_pos),
                    (x_pos, y_pos, z_pos + 1),
                    (x_pos, y_pos, z_pos + 2)
                ]

                if not any(
                    coordinate in spawn_area
                    for coordinate in line
                ):
                    valid_lines.append(line)

        if not valid_lines:
            raise ValueError(
                "Could not find a valid three-block line "
                "outside the central 3x3 spawn area."
            )

        line = random.choice(valid_lines)

        self.blocks = {
            "blue_wool": 3
        }

        self.blocks_position = {
            "blue_wool": line
        }

    # -------------------------------------------------------------------------
    # BLOCK PLACEMENT
    # -------------------------------------------------------------------------

    def set_blocks(self):
        """
        Place the blocks stored in self.blocks_position.

        No randomness occurs here.
        """

        if self.blocks_position is None:
            raise RuntimeError(
                "blocks_position is not initialized. "
                "Call initialize() first."
            )

        for block_type, coordinates in self.blocks_position.items():

            for x_pos, y_pos, z_pos in coordinates:

                time.sleep(0.00001)

                self.minecraft_server.send(
                    f"setblock {x_pos} {y_pos} {z_pos} "
                    f"minecraft:{block_type}"
                )

    # -------------------------------------------------------------------------
    # SCENARIO RESET
    # -------------------------------------------------------------------------

    def reset_scenario(self):
        """
        Reset the arena and spawn the initial blocks for the selected scenario.

        This should be called at the beginning of each episode/round.
        """

        # Remove blocks left by the previous episode.
        self.reset_arena_interior()

        if self.scenario == "empty":
            # Nothing is spawned.
            return

        if self.blocks_position is None:
            raise RuntimeError(
                "No block configuration exists. "
                "Call initialize() first."
            )

        self.set_blocks()

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------

    def cleanup(self, radius: int = 15, clear_height: int = 6):
        """
        Remove the complete arena and surrounding structures.
        """

        x0 = self.origin[0] - radius
        y0 = self.origin[1]
        z0 = self.origin[2] - radius

        sx = self.size[0] + 2 * radius
        sy = clear_height
        sz = self.size[2] + 2 * radius

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} "
            f"{sx} {sy} {sz} "
            f"minecraft:{BlockTypes.AIR.value}"
        )

        self._static_built = False

    # -------------------------------------------------------------------------
    # RANDOM POINT
    # -------------------------------------------------------------------------

    def get_point_in_environment(self):
        """
        Return a random point inside the playable arena.
        """

        return (
            random.randint(
                self.origin[0] + 1,
                self.origin[0] + self.size[0] - 2
            ),
            self.origin[1] + 1,
            random.randint(
                self.origin[2] + 1,
                self.origin[2] + self.size[2] - 2
            )
        )
import random
import time
from typing import override

from swarmcraft.environment import Environment
from swarmcraft.util import add_tuples
from swarmcraft import BlockTypes


class ForageEnvironment(Environment):
    def __init__(self, minecraft_server, origin, size):
        super().__init__(minecraft_server)
        self.origin = origin
        self.size = size
        self.resource_positions = []

        # Block spec (type -> count) and fixed per-experiment positions
        self.blocks = None
        self.blocks_position = None  # {"blue_wool": [(x,y,z), ...], ...}

        # Ensures bedrock walls/floor, stairs, and roof are only built once
        self._static_built = False

    def clean_environment(self, radius: int = 15, clear_height: int = 4):
        """
        Clear a large area around the arena by setting everything to air.

        Variables
        ----------
        radius : int
            How far to clear beyond the arena bounds in X/Z directions.
        clear_height : int
            How many blocks high (starting at origin.y) to clear.
        """
        x0 = self.origin[0] - radius
        y0 = self.origin[1]
        z0 = self.origin[2] - radius

        sx = self.size[0] + 2 * radius
        sy = clear_height
        sz = self.size[2] + 2 * radius

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} {sx} {sy} {sz} minecraft:{BlockTypes.AIR.value}"
        )

    def reset_arena_interior(self):
        """
        Clear ONLY the interior play area (where wool blocks spawn), leaving:
        - bedrock floor
        - bedrock perimeter walls
        - observer stairs
        - glass roof

        Interior region definition:
        - x in [origin.x+1 .. origin.x+size.x-2]
        - z in [origin.z+1 .. origin.z+size.z-2]
        - y is only the block layer where resources are placed: origin.y+1 (height 1 above floor)

        This matches your current spawning y_pos = origin.y + 1.
        """
        if self.size[0] < 3 or self.size[2] < 3:
            return  # no interior exists

        x0 = self.origin[0] + 1
        y0 = self.origin[1] + 1
        z0 = self.origin[2] + 1

        sx = self.size[0] - 2
        sy = 1
        sz = self.size[2] - 2

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} {sx} {sy} {sz} minecraft:{BlockTypes.AIR.value}"
        )

    @override
    def reset(self):
        """
        Backwards-compatible reset method.

        For your new workflow you should NOT wipe the whole arena volume each round,
        because that would remove walls/floor. Therefore, reset() now clears only
        the interior resource layer.
        """
        self.reset_arena_interior()

    def _build_bedrock_arena(self):
        """
        Build the bedrock floor and 2-high perimeter walls.

        Variables
        ----------
        origin : tuple[int,int,int]
            Arena corner (x,y,z).
        size : tuple[int,int,int]
            Arena dimensions (sx,sy,sz).
        """
        ox, oy, oz = self.origin
        sx = self.size[0]
        sz = self.size[2]
        bedrock = f"minecraft:{BlockTypes.BEDROCK.value}"

        # Floor: y = oy, height 1
        self.minecraft_server.send(
            f"setcube {ox} {oy} {oz} {sx} 1 {sz} {bedrock}"
        )

        # Walls: y = oy+1, height 2 (matches the old per-column two-block stack)
        wall_y = oy + 1
        wall_h = 2

        # North wall (z = oz), thickness 1
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz} {sx} {wall_h} 1 {bedrock}"
        )

        # South wall (z = oz + sz - 1), thickness 1
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz + sz - 1} {sx} {wall_h} 1 {bedrock}"
        )

        # West wall (x = ox), thickness 1
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz} 1 {wall_h} {sz} {bedrock}"
        )

        # East wall (x = ox + sx - 1), thickness 1
        self.minecraft_server.send(
            f"setcube {ox + sx - 1} {wall_y} {oz} 1 {wall_h} {sz} {bedrock}"
        )

    def _build_observer_stairs(self):
        """
        Build grass stairs along one entire side of the arena.

        Adjustments:
        - 1-block gap to arena: stairs start at z = origin.z - 2
        - start one block lower: base_y = origin.y
        - wedge heights: 5,4,3,2,1 (five rows)
        """
        base_y = self.origin[1]
        z_edge = self.origin[2] - 2
        stone = f"minecraft:{BlockTypes.STONE_BRICK.value}"

        # Solid wedge (5 layers). The duplicate loop in the original code is removed.
        for step_idx in range(5):
            height = 5 - step_idx
            z = z_edge - step_idx
            self.minecraft_server.send(
                f"setcube {self.origin[0]} {base_y} {z} "
                f"{self.size[0]} {height} 1 {stone}"
            )

        # Stairs on top (block state requires vanilla command path in your current design)
        stairs_block = f"minecraft:{BlockTypes.STONE_BRICK_STAIRS.value}[facing=south,half=bottom]"
        x1 = self.origin[0]
        x2 = self.origin[0] + self.size[0] - 1

        for step_idx in range(6):
            height = 6 - step_idx
            z = z_edge - step_idx + 1
            y_stairs = base_y + height
            self.minecraft_server.send(
                f"command fill {x1} {y_stairs} {z} {x2} {y_stairs} {z} {stairs_block}"
            )

        z_ground = z_edge - 5
        self.minecraft_server.send(
            f"command fill {x1} {base_y} {z_ground} {x2} {base_y} {z_ground} {stairs_block}"
        )

    def _build_glass_roof(self):
        """
        Place a glass roof above the whole arena at height 5 relative to floor.

        Variables
        ----------
        y : int
            Roof y-level = origin.y + 5
        """
        y = self.origin[1] + 5
        glass = f"minecraft:{BlockTypes.GLASS.value}"
        self.minecraft_server.send(
            f"setcube {self.origin[0] - 1} {y} {self.origin[2] - 1} "
            f"{self.size[0] + 2} 1 {self.size[2] + 2} {glass}"
        )

    def build_static_structures_once(self):
        """
        Build static structures once per environment:
        - optional full clean in radius
        - bedrock arena
        - grass stairs
        - glass roof

        Variables
        ----------
        do_clean : bool
            If True, calls clean_environment() before building structures.
        """
        if self._static_built:
            return
        self._build_bedrock_arena()
        self._build_observer_stairs()
        self._build_glass_roof()
        self._static_built = True

    def build_bridge_to(self, other_origin: tuple[int, int, int]) -> None:
        """
        Build a 1-block-thick glass bridge between this arena's roof rectangle and another's.

        Requirements (enforced):
        - Roof heights must match (same y = origin.y + 5).
        - Arenas must be separated along exactly one axis (x OR z), not diagonally.
        - Roof rectangles should overlap on the perpendicular axis; otherwise we raise.
        """
        y1 = self.origin[1] + 5
        y2 = other_origin[1] + 5
        if y1 != y2:
            raise ValueError(f"Roof heights differ (self={y1}, other={y2}); cannot build a flat bridge.")

        self_xmin = self.origin[0] - 1
        self_xmax = self.origin[0] + self.size[0]
        self_zmin = self.origin[2] - 1
        self_zmax = self.origin[2] + self.size[2]

        oth_xmin = other_origin[0] - 1
        oth_xmax = other_origin[0] + self.size[0]
        oth_zmin = other_origin[2] - 1
        oth_zmax = other_origin[2] + self.size[2]

        x_separated = (self_xmax < oth_xmin) or (oth_xmax < self_xmin)
        z_separated = (self_zmax < oth_zmin) or (oth_zmax < self_zmin)

        if x_separated and z_separated:
            raise ValueError("Roofs are diagonally separated (gap in both x and z); provide a custom bridge plan.")
        if not x_separated and not z_separated:
            return

        glass = f"minecraft:{BlockTypes.GLASS.value}"

        if x_separated:
            # bridge along x; require overlap in z
            z1 = max(self_zmin, oth_zmin)
            z2 = min(self_zmax, oth_zmax)
            if z1 > z2:
                raise ValueError("Roofs do not overlap in z; cannot infer bridge span.")

            x1 = min(self_xmax, oth_xmax)
            x2 = max(self_xmin, oth_xmin)
            # The above is not correct for the bridge span; compute edge-to-edge instead:
            if self_xmax < oth_xmin:
                x1, x2 = self_xmax, oth_xmin
            else:
                x1, x2 = oth_xmax, self_xmin

            self.minecraft_server.send(
                f"command fill {x1} {y1} {z1} {x2} {y1} {z2} {glass}"
            )
        else:
            x1 = max(self_xmin, oth_xmin)
            x2 = min(self_xmax, oth_xmax)
            if x1 > x2:
                raise ValueError("Roofs do not overlap in x; cannot infer bridge span.")

            if self_zmax < oth_zmin:
                z1, z2 = self_zmax, oth_zmin
            else:
                z1, z2 = oth_zmax, self_zmin

            self.minecraft_server.send(
                f"command fill {x1} {y1} {z1} {x2} {y1} {z2} {glass}"
            )

    @override
    def initialize(self):
        """
        Initialize the environment.

        New behavior:
        - Ensure static structures exist (only once)
        - Do NOT clear them afterward
        """
        self.build_static_structures_once()

    def shuffle_block_positions(self, blocks=None):
        """
        Compute and store a fresh random (but then fixed) set of block positions in self.blocks_position.

        Workflow:
        - Call shuffle_block_positions() once per experiment (or whenever you want a new layout).
        - Each round call reset_arena_interior() then set_blocks(); set_blocks uses ONLY these stored positions.

        Parameters
        ----------
        blocks : dict[str,int] | None
            Block-type -> count; if None, uses default.
        seed : int | None
            If provided, makes the shuffle deterministic for reproducibility.
        """
        if blocks is None:
            blocks = {"blue_wool": 4, "orange_wool": 4, "brown_wool": 0, "green_wool": 0}

        self.blocks = dict(blocks)

        if self.size[0] < 3 or self.size[2] < 3:
            self.blocks_position = {bt: [] for bt in self.blocks}
            return

        # Reserve center tile (agent spawn / no resource placement)
        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2
        reserved = (center_x, self.origin[1] + 1, center_z)

        interior_w = self.size[0] - 2
        interior_d = self.size[2] - 2
        capacity = interior_w * interior_d - 1  # minus reserved
        total_needed = sum(int(c) for c in self.blocks.values())
        if total_needed > capacity:
            raise ValueError(
                f"Too many blocks requested ({total_needed}) for interior capacity ({capacity}) "
                f"given arena size={self.size} and one reserved center tile."
            )

        occupied = {reserved}
        positions: dict[str, list[tuple[int, int, int]]] = {bt: [] for bt in self.blocks}

        for block_type, count in self.blocks.items():
            for _ in range(int(count)):
                while True:
                    x_pos = random.randint(self.origin[0] + 1, self.origin[0] + self.size[0] - 2)
                    z_pos = random.randint(self.origin[2] + 1, self.origin[2] + self.size[2] - 2)
                    y_pos = self.origin[1] + 1
                    coord = (x_pos, y_pos, z_pos)
                    if coord not in occupied:
                        occupied.add(coord)
                        positions[block_type].append(coord)
                        break

        self.blocks_position = positions

    def set_blocks(self):
        """
        Spawn wool blocks at the fixed locations stored in self.blocks_position.

        Contract:
        - shuffle_block_positions() MUST be called before the first call to set_blocks().
        - No randomness occurs here; only stored positions are used.
        - Assumes reset_arena_interior() has been called before this.
        """
        if self.blocks_position is None:
            raise RuntimeError(
                "blocks_position is not initialized. Call shuffle_block_positions() once before set_blocks()."
            )
        print("Blocks: ", self.blocks_position)

        for block_type, coords in self.blocks_position.items():
            for (x_pos, y_pos, z_pos) in coords:
                time.sleep(0.00001)
                self.minecraft_server.send(
                    f"setblock {x_pos} {y_pos} {z_pos} minecraft:{block_type}"
                )

    def cleanup(self, radius: int = 15, clear_height: int = 6):
        """
        Destroy all structures previously built by this environment so the world is flat again.

        This clears to AIR a box that covers:
        - the bedrock arena floor and perimeter walls,
        - the observer stairs region in front of the arena,
        - the glass roof above the arena,
        - any leftover resource blocks placed inside the arena,
        - plus a configurable radius margin.

        Parameters
        ----------
        radius : int
            Horizontal padding (in blocks) around the arena in X/Z to clear.
            Must be large enough to include stairs area and any other artifacts.
        clear_height : int
            Vertical height to clear starting at origin.y (inclusive).
            Must be >= 6 to remove:
              - stairs (up to height 5),
              - roof at y = origin.y + 5.
        """
        x0 = self.origin[0] - radius
        y0 = self.origin[1]
        z0 = self.origin[2] - radius

        sx = self.size[0] + 2 * radius
        sy = clear_height
        sz = self.size[2] + 2 * radius

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} {sx} {sy} {sz} minecraft:{BlockTypes.AIR.value}"
        )

        # Reset static-built flag so a future initialize() rebuilds everything cleanly.
        self._static_built = False

    def get_point_in_environment(self):
        return (
            random.randint(self.origin[0] + 1, self.origin[0] + self.size[0]),
            self.origin[1] + 1,
            random.randint(self.origin[2] + 1, self.origin[2] + self.size[2]),
        )

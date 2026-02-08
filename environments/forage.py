import random
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
        self.blocks = None

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
        # floor at y = origin.y
        self.minecraft_server.send(
            f"setcube {self.origin[0]} {self.origin[1]} {self.origin[2]} "
            f"{self.size[0]} 1 {self.size[2]} minecraft:{BlockTypes.BEDROCK.value}"
        )

        # perimeter walls at y = origin.y + 1 and y = origin.y + 2
        for x in range(self.size[0]):
            for z in range(self.size[2]):
                if x == 0 or x == self.size[0] - 1 or z == 0 or z == self.size[2] - 1:
                    px, py, pz = add_tuples(self.origin, (x, 1, z))
                    self.minecraft_server.send(
                        f"setblock {px} {py} {pz} minecraft:{BlockTypes.BEDROCK.value}"
                    )
                    self.minecraft_server.send(
                        f"setblock {px} {py + 1} {pz} minecraft:{BlockTypes.BEDROCK.value}"
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

        for step_idx in range(5):
            height = 5 - step_idx
            z = z_edge - step_idx
            self.minecraft_server.send(
                f"setcube {self.origin[0]} {base_y} {z} "
                f"{self.size[0]} {height} 1 minecraft:{BlockTypes.STONE_BRICK.value}"
            )

        for step_idx in range(5):
            height = 5 - step_idx
            z = z_edge - step_idx
            self.minecraft_server.send(
                f"setcube {self.origin[0]} {base_y} {z} "
                f"{self.size[0]} {height} 1 minecraft:{BlockTypes.STONE_BRICK.value}"
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
        self.minecraft_server.send(
            f"setcube {self.origin[0]} {y} {self.origin[2]} "
            f"{self.size[0]} 1 {self.size[2]} minecraft:{BlockTypes.GLASS.value}"
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

    @override
    def initialize(self):
        """
        Initialize the environment.

        New behavior:
        - Ensure static structures exist (only once)
        - Do NOT clear them afterward
        """
        self.build_static_structures_once()

    def set_blocks(self, blocks=None):
        """
        Spawn wool blocks within the bedrock perimeter at unique locations.

        Important:
        - Assumes reset_arena_interior() has been called before this, so no stale wool remains.
        """
        if blocks is None:
            blocks = {"blue_wool": 4, "orange_wool": 4, "brown_wool": 0, "green_wool": 0}

        self.blocks = blocks

        occupied_coords = set()
        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2
        occupied_coords.add((center_x, self.origin[1] + 1, center_z))

        for block_type, count in self.blocks.items():
            for _ in range(count):
                while True:
                    x_pos = random.randint(self.origin[0] + 1, self.origin[0] + self.size[0] - 2)
                    z_pos = random.randint(self.origin[2] + 1, self.origin[2] + self.size[2] - 2)
                    y_pos = self.origin[1] + 1

                    coord = (x_pos, y_pos, z_pos)

                    if coord not in occupied_coords:
                        occupied_coords.add(coord)
                        self.minecraft_server.send(
                            f"setblock {x_pos} {y_pos} {z_pos} minecraft:{block_type}"
                        )
                        break

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

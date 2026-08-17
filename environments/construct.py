import random
import time
from typing import override

from swarmcraft.environment import Environment
from swarmcraft.util import add_tuples
from swarmcraft import BlockTypes


class ConstructionEnvironment(Environment):
    def __init__(self, minecraft_server, origin, size):
        super().__init__(minecraft_server)
        self.origin = origin
        self.size = size

        # Ensures bedrock walls/floor, stairs, and roof are only built once
        self._static_built = False

    def get_center_position(self) -> tuple[int, int, int]:
        """
        Returns the center spawn coordinate of the arena floor.
        """
        center_x = self.origin[0] + self.size[0] // 2
        center_y = self.origin[1] + 1
        center_z = self.origin[2] + self.size[2] // 2
        return (center_x, center_y, center_z)

    def clean_environment(self, radius: int = 15, clear_height: int = 6):
        """
        Clear a large area around the arena by setting everything to air.
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
        Clear ONLY the interior play area (all height levels under the glass roof),
        leaving intact:
        - bedrock floor
        - bedrock perimeter walls
        - observer stairs
        - glass roof
        """
        if self.size[0] < 3 or self.size[2] < 3:
            return  # no interior exists

        x0 = self.origin[0] + 1
        y0 = self.origin[1] + 1
        z0 = self.origin[2] + 1

        sx = self.size[0] - 2
        sy = 4  # Clears all 4 vertical block levels up to the glass roof
        sz = self.size[2] - 2

        self.minecraft_server.send(
            f"setcube {x0} {y0} {z0} {sx} {sy} {sz} minecraft:{BlockTypes.AIR.value}"
        )

    @override
    def reset(self):
        """
        Resets the interior area to air for the next construction round.
        """
        self.reset_arena_interior()

    def _build_bedrock_arena(self):
        """
        Build the bedrock floor and 2-high perimeter walls.
        """
        ox, oy, oz = self.origin
        sx = self.size[0]
        sz = self.size[2]
        bedrock = f"minecraft:{BlockTypes.BEDROCK.value}"

        # Floor: y = oy, height 1
        self.minecraft_server.send(
            f"setcube {ox} {oy} {oz} {sx} 1 {sz} {bedrock}"
        )

        # Walls: y = oy+1, height 2
        wall_y = oy + 1
        wall_h = 2

        # North wall (z = oz)
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz} {sx} {wall_h} 1 {bedrock}"
        )

        # South wall (z = oz + sz - 1)
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz + sz - 1} {sx} {wall_h} 1 {bedrock}"
        )

        # West wall (x = ox)
        self.minecraft_server.send(
            f"setcube {ox} {wall_y} {oz} 1 {wall_h} {sz} {bedrock}"
        )

        # East wall (x = ox + sx - 1)
        self.minecraft_server.send(
            f"setcube {ox + sx - 1} {wall_y} {oz} 1 {wall_h} {sz} {bedrock}"
        )

    def _build_observer_stairs(self):
        """
        Build grass stairs along one entire side of the arena.
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
        """
        y = self.origin[1] + 5
        glass = f"minecraft:{BlockTypes.GLASS.value}"
        self.minecraft_server.send(
            f"setcube {self.origin[0] - 1} {y} {self.origin[2] - 1} "
            f"{self.size[0] + 2} 1 {self.size[2] + 2} {glass}"
        )

    def build_static_structures_once(self):
        """
        Build static structures once per environment.
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
            raise ValueError("Roofs are diagonally separated; provide a custom bridge plan.")
        if not x_separated and not z_separated:
            return

        glass = f"minecraft:{BlockTypes.GLASS.value}"

        if x_separated:
            z1 = max(self_zmin, oth_zmin)
            z2 = min(self_zmax, oth_zmax)
            if z1 > z2:
                raise ValueError("Roofs do not overlap in z; cannot infer bridge span.")

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
        Initialize static structures for construction arena.
        """
        self.build_static_structures_once()

    def shuffle_block_positions(self, blocks=None):
        """
        No-op for construction scenarios since no resource blocks are placed.
        """
        pass

    def set_blocks(self):
        """
        Ensures arena field remains completely clear at the start of each round.
        """
        self.reset_arena_interior()

    def cleanup(self, radius: int = 15, clear_height: int = 6):
        """
        Destroy all structures previously built by this environment.
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
        self._static_built = False

    def get_point_in_environment(self):
        return (
            random.randint(self.origin[0] + 1, self.origin[0] + self.size[0] - 2),
            self.origin[1] + 1,
            random.randint(self.origin[2] + 1, self.origin[2] + self.size[2] - 2),
        )
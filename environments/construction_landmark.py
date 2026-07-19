"""
Environment for a construction-oriented mission: instead of scattered
resource blocks, the arena contains exactly two landmark blocks marking
the segment agents should build across (this lines up with the
commented-out "Future Tier 3: Construction" primitives already sketched
in shell.py's generate_pset() -- PlaceBlockRelative, FaceStructureEnd,
MoveToStructureEnd, IsStructureAhead -- which will presumably want
something to sense/navigate toward).

Reuses ForageEnvironment's arena scaffold (bedrock walls/floor, observer
stairs, glass roof, inter-arena bridges, cleanup) unchanged; only block
placement (shuffle_block_positions) is overridden.

Note on inheriting from ForageEnvironment: same tradeoff as
clustered_forage.py -- done to reuse the arena scaffold, not because a
construction task conceptually "is a" forage task. Worth revisiting with
a shared ArenaEnvironment(Environment) base if a third non-forage
mission shows up.
"""
import random
from typing import Optional

from environments.forage import ForageEnvironment


class ConstructionLandmarkEnvironment(ForageEnvironment):
    """
    Places exactly two landmark blocks a configurable distance apart,
    symmetric about the arena's interior center, on a randomly chosen
    axis each round (so agents can't hardcode a compass direction).
    Everything else -- arena scaffold, cleanup, reset -- is inherited
    unchanged from ForageEnvironment.

    Variables
    ---------
    minecraft_server, origin, size : as in ForageEnvironment.
    separation : int
        Distance in blocks between the two landmarks. Clamped to fit the
        interior (and to stay at least 2, so neither landmark lands
        exactly on the reserved agent-spawn point at arena center) --
        only relaxed if the arena is too small to support that. Larger
        values make locating both landmarks -- and building between them
        -- harder, which is a natural curriculum knob for later missions.
    landmark_block : str
        Block type used for both landmarks.
    """

    def __init__(
        self,
        minecraft_server,
        origin,
        size,
        separation: int = 6,
        landmark_block: str = "blue_wool",
    ):
        super().__init__(minecraft_server, origin, size)
        self.separation = separation
        self.landmark_block = landmark_block

    def shuffle_block_positions(self, blocks: Optional[dict] = None) -> None:
        """
        Place the two landmark blocks.

        `blocks` is accepted only so this environment is a drop-in for
        callers that always pass a blocks dict (e.g.
        ForageExperiment.shuffle_block_positions); its contents are
        ignored, since block type/count aren't meaningful here -- this
        environment always places exactly 2 blocks of landmark_block.

        Returns
        -------
        None
        """
        if self.size[0] < 3 or self.size[2] < 3:
            self.blocks = {self.landmark_block: 0}
            self.blocks_position = {self.landmark_block: []}
            return

        x_min, x_max = self.origin[0] + 1, self.origin[0] + self.size[0] - 2
        z_min, z_max = self.origin[2] + 1, self.origin[2] + self.size[2] - 2
        y_pos = self.origin[1] + 1

        interior_w = x_max - x_min + 1
        interior_d = z_max - z_min + 1
        max_separation = max(1, min(interior_w, interior_d) - 1)

        separation = max(1, min(int(self.separation), max_separation))
        if max_separation >= 2:
            separation = max(2, separation)
        half = separation // 2

        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2

        axis = random.choice(("x", "z"))
        if axis == "x":
            p1 = (center_x - half, y_pos, center_z)
            p2 = (center_x - half + separation, y_pos, center_z)
        else:
            p1 = (center_x, y_pos, center_z - half)
            p2 = (center_x, y_pos, center_z - half + separation)

        def _clip(pos):
            x, y, z = pos
            return (max(x_min, min(x_max, x)), y, max(z_min, min(z_max, z)))

        p1, p2 = _clip(p1), _clip(p2)

        self.blocks = {self.landmark_block: 2}
        self.blocks_position = {self.landmark_block: [p1, p2]}
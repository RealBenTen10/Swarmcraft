"""
Environment for Curriculum Tier 1 (foraging), generalized so the spatial
distribution of the single resource block type is tunable -- from
uniformly random, through several loose clusters, down to one tight
cluster -- via num_clusters and cluster_spread.

Reuses ForageEnvironment's arena scaffold (bedrock walls/floor, observer
stairs, glass roof, inter-arena bridges, cleanup) unchanged; only block
placement (shuffle_block_positions) is overridden.

Note on inheriting from ForageEnvironment: this is done purely to reuse
the arena-scaffold building blocks, not because a tunable-density forage
task "is a" ForageEnvironment in a conceptual sense. If more non-forage
missions get added later (e.g. construction_landmark.py), it's worth
extracting a shared ArenaEnvironment(Environment) base that just owns the
bedrock/stairs/roof/bridge/cleanup code, with ForageEnvironment and its
siblings all sitting beside each other as siblings instead of one
inheriting the others' name.
"""
import random
from typing import Optional

from environments.forage import ForageEnvironment


class ClusteredForageEnvironment(ForageEnvironment):
    """
    Forage environment with a single resource block type whose placement
    can be tuned from fully random to tightly clustered.

    Density/clustering model
    -------------------------
    num_clusters cluster centers are drawn uniformly at random over the
    interior. Each block's position is then drawn from a 2D Gaussian
    centered on a randomly chosen cluster (std dev = cluster_spread),
    rounded to the nearest block, clipped to the interior, and
    rejection-sampled against already-occupied coordinates -- the same
    approach ForageEnvironment already uses for its own placement.

    - num_clusters=None (or 0): no cluster centers at all, so every block
      is drawn uniformly over the whole interior -- identical to
      ForageEnvironment's current behavior.
    - num_clusters=1: a single cluster; cluster_spread controls how tight
      it is (small spread = dense pile; spread comparable to the arena
      size approaches uniform).
    - num_clusters=k>1: k clusters, each block belonging to a randomly
      chosen one.

    num_clusters/cluster_spread are plain mutable attributes (like
    self.blocks elsewhere in this codebase) rather than method
    parameters, so a future per-generation curriculum can vary them the
    same way mission_for_generation varies the target mission -- just
    set env.num_clusters/env.cluster_spread before the next
    shuffle_block_positions() call.

    Variables
    ---------
    minecraft_server, origin, size : as in ForageEnvironment.
    num_clusters : int | None
        Number of cluster centers. None or 0 means fully random (default).
    cluster_spread : float
        Standard deviation, in blocks, of each cluster. Only relevant
        when num_clusters is set.
    default_block_type : str
        Block type used when shuffle_block_positions() is called with
        blocks=None.
    default_count : int
        Count used when shuffle_block_positions() is called with
        blocks=None.
    """

    def __init__(
        self,
        minecraft_server,
        origin,
        size,
        num_clusters: Optional[int] = None,
        cluster_spread: float = 6.0,
        default_block_type: str = "blue_wool",
        default_count: int = 8,
    ):
        super().__init__(minecraft_server, origin, size)
        self.num_clusters = num_clusters
        self.cluster_spread = cluster_spread
        self.default_block_type = default_block_type
        self.default_count = default_count

    def _extract_single_block_spec(self, blocks: Optional[dict]) -> tuple[str, int]:
        """
        Reduce a (possibly multi-color, ForageEnvironment-style) blocks
        dict down to the single (block_type, count) pair this environment
        actually places, since only one resource type is meaningful here.

        Variables
        ---------
        blocks : dict[str, int] | None
            Block-type -> count, as passed by ForageExperiment. If None
            or empty, falls back to (default_block_type, default_count).

        Returns
        -------
        tuple[str, int]
            The block type and count to place this round.
        """
        if not blocks:
            return self.default_block_type, self.default_count

        nonzero = [(bt, int(c)) for bt, c in blocks.items() if int(c) > 0]
        if not nonzero:
            return self.default_block_type, 0
        if len(nonzero) > 1:
            print(
                f"ClusteredForageEnvironment: got multiple block types with "
                f"nonzero count {nonzero}; this environment places one type "
                f"per round, using {nonzero[0][0]!r} and ignoring the rest."
            )
        return nonzero[0]

    def _sample_position(
        self,
        cluster_centers: list,
        bounds: tuple,
    ) -> tuple:
        """
        Draw one (x, z) position: uniformly if there are no cluster
        centers, otherwise from a Gaussian around a randomly chosen one.
        """
        x_min, x_max, z_min, z_max = bounds

        if not cluster_centers:
            return random.randint(x_min, x_max), random.randint(z_min, z_max)

        cx, cz = random.choice(cluster_centers)
        x = int(round(random.gauss(cx, self.cluster_spread)))
        z = int(round(random.gauss(cz, self.cluster_spread)))
        x = max(x_min, min(x_max, x))
        z = max(z_min, min(z_max, z))
        return x, z

    def shuffle_block_positions(self, blocks: Optional[dict] = None) -> None:
        """
        Compute and store fresh block positions using the tunable
        clustering model described on the class.

        Variables
        ---------
        blocks : dict[str, int] | None
            Only a single (block_type, count) pair is used -- see
            _extract_single_block_spec.

        Returns
        -------
        None
        """
        block_type, count = self._extract_single_block_spec(blocks)
        self.blocks = {block_type: count}

        if self.size[0] < 3 or self.size[2] < 3:
            self.blocks_position = {block_type: []}
            return

        x_min, x_max = self.origin[0] + 1, self.origin[0] + self.size[0] - 2
        z_min, z_max = self.origin[2] + 1, self.origin[2] + self.size[2] - 2
        bounds = (x_min, x_max, z_min, z_max)
        y_pos = self.origin[1] + 1

        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2
        reserved = (center_x, y_pos, center_z)

        capacity = (x_max - x_min + 1) * (z_max - z_min + 1) - 1
        if count > capacity:
            raise ValueError(
                f"Requested {count} blocks exceeds interior capacity "
                f"({capacity}) for arena size={self.size}."
            )

        cluster_centers = []
        if self.num_clusters:
            for _ in range(int(self.num_clusters)):
                cluster_centers.append(
                    (random.randint(x_min, x_max), random.randint(z_min, z_max))
                )

        occupied = {reserved}
        positions = []
        for _ in range(int(count)):
            placed = False
            for _attempt in range(200):
                x_pos, z_pos = self._sample_position(cluster_centers, bounds)
                coord = (x_pos, y_pos, z_pos)
                if coord not in occupied:
                    occupied.add(coord)
                    positions.append(coord)
                    placed = True
                    break
            if not placed:
                # A very tight cluster_spread relative to remaining free
                # cells can starve rejection sampling near capacity; fall
                # back to a uniform draw so this always terminates
                # instead of spinning indefinitely.
                while True:
                    x_pos = random.randint(x_min, x_max)
                    z_pos = random.randint(z_min, z_max)
                    coord = (x_pos, y_pos, z_pos)
                    if coord not in occupied:
                        occupied.add(coord)
                        positions.append(coord)
                        break

        self.blocks_position = {block_type: positions}
import math
import time

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import SequenceNode, FallbackNode
from swarmcraft.btree.nodes.actuation import (
    StartDig,
    PressDir,
    Rotate,
    ReleaseDir,
    SendMessage,
    Pathfinder,
    PlaceForward,
    NavigateToColor,
    NavigateOneBlock,
    MoveToReceivedCoordinate,
    BroadcastLocation,
)
from swarmcraft.btree.nodes.sensing import (
    SenseBlock,
    GotMessage,
    SenseBlockFront,
)
from swarmcraft import BlockTypes


class ForageAgent(Agent):
    """
    Agent for the foraging/construction experiments.

    Supported fitness functions:

        S1 - Find blocks
        S2 - Destroy and collect blocks
        S3 - Find current line
        S4 - Extend current line

    The fitness function is selected by the `fitness_function` constructor
    argument, e.g. "S1", "S2", "S3", or "S4".

    Expected environment/sensing interfaces used by the fitness functions:

        environment.get_distance_to_nearest_block(position)
        environment.get_distance_to_longest_line(position)
        environment.get_longest_line_length()

        sensing.get_inventory()

        sensing.get_blocks_in_arena(origin, size, blocks)

    The three environment functions can be implemented later; they are
    deliberately kept outside the agent.
    """

    BLUE_WOOL = "blue_wool"


    def __init__(
        self,
        pooler,
        message_server,
        uid,
        start_location,
        env,
        parent_uid=None,
        fitness_function="S1",
        distance_scale=1.0,
    ):
        super().__init__(pooler, message_server, uid)

        self.start_location = start_location
        self.environment = env
        self.parent_uid = parent_uid

        # Fitness configuration
        self.fitness_function = fitness_function
        self.distance_scale = distance_scale

        if self.fitness_function not in self.VALID_FITNESS_FUNCTIONS:
            raise ValueError(
                f"Unknown fitness function '{self.fitness_function}'. "
                f"Supported functions: {sorted(self.VALID_FITNESS_FUNCTIONS)}"
            )

        # Behavior tree
        self.tree = None

        # Movement tracking
        self.positions = []

        # ------------------------------------------------------------------
        # Fitness state
        # ------------------------------------------------------------------

        # Lazily initialized on the first tick after the environment has
        # been populated with blocks.
        self._fitness_initialized = False

        # S1/S3: accumulated distance reward over ticks
        self._distance_fitness_sum = 0.0
        self._fitness_tick_count = 0

        # S2/S4: previous world state
        self._previous_arena_block_count = None
        self._previous_inventory_count = None
        self._previous_longest_line_length = None

        # S2/S4: accumulated event fitness
        self._event_fitness = 0.0

    # ----------------------------------------------------------------------
    # Behavior tree
    # ----------------------------------------------------------------------

    def set_tree(self, tree):
        self.tree = tree

    def update(self):
        self.movement_tracker()

        if self.tree is None:
            return

        # Execute one behavior-tree tick first.
        self.tree.tick()

        # Evaluate the resulting state of this tick.
        self._update_fitness()

    # ----------------------------------------------------------------------
    # Reset
    # ----------------------------------------------------------------------

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

            self._reset_fitness_state()

        except Exception as e:
            print(f"Error while resetting agent: {e}")

    def _reset_fitness_state(self):
        """
        Reset all fitness state.

        The actual world state is intentionally not read here because reset()
        can happen before the experiment has placed the blocks. The initial
        fitness state is therefore initialized lazily on the first update().
        """
        self._fitness_initialized = False

        self._distance_fitness_sum = 0.0
        self._fitness_tick_count = 0

        self._previous_arena_block_count = None
        self._previous_inventory_count = None
        self._previous_longest_line_length = None

        self._event_fitness = 0.0

    # ----------------------------------------------------------------------
    # Movement tracking
    # ----------------------------------------------------------------------

    def movement_tracker(self):
        pos = self.sensing.get_position()
        rounded = tuple(round(x) for x in pos)

        if rounded not in self.positions:
            self.positions.append(rounded)

    # ----------------------------------------------------------------------
    # Fitness configuration
    # ----------------------------------------------------------------------

    def set_fitness_function(self, fitness_function):
        if fitness_function not in self.VALID_FITNESS_FUNCTIONS:
            raise ValueError(
                f"Unknown fitness function '{fitness_function}'. "
                f"Supported functions: {sorted(self.VALID_FITNESS_FUNCTIONS)}"
            )

        self.fitness_function = fitness_function
        self._reset_fitness_state()

    # ----------------------------------------------------------------------
    # Generic fitness update
    # ----------------------------------------------------------------------

    def _update_fitness(self):
        """
        Update fitness once per behavior-tree tick.

        S1/S3:
            Reward is based on distance and averaged over ticks.

        S2/S4:
            Reward/penalties are based on changes in world/inventory state.
        """

        if not self._fitness_initialized:
            self._initialize_fitness_state()

        if self.fitness_function == "S1":
            self._update_s1()

        elif self.fitness_function == "S2":
            self._update_s2()

        elif self.fitness_function == "S3":
            self._update_s3()

        elif self.fitness_function == "S4":
            self._update_s4()

    def _initialize_fitness_state(self):
        """
        Store the state before the first evaluated tick.

        This must happen after the environment has created the blocks.
        """

        self._previous_arena_block_count = self._get_blue_wool_count()
        self._previous_inventory_count = self._get_blue_wool_inventory_count()

        if self.fitness_function == "S4":
            self._previous_longest_line_length = (
                self._get_longest_line_length()
            )

        self._fitness_initialized = True

    # ----------------------------------------------------------------------
    # S1 - Find blocks
    # ----------------------------------------------------------------------

    def _update_s1(self):
        """
        S1: Find blocks.

        Every tick:
            reward = exp(-distance / distance_scale)

        Maximum reward:
            1.0 when distance == 0

        Therefore:
            distance 0  -> 1.0
            distance 1  -> exp(-1)
            distance 2  -> exp(-2)
            ...

        Standing still close to a block continues to generate a reward,
        which is explicitly allowed for this fitness function.
        """

        distance = self.sensing.get_distance_to_next_block(BlockTypes.BLUE_WOOL)

        if distance is None:
            reward = 0.0
        else:
            if distance < 0:
                raise ValueError(
                    f"Distance to nearest block cannot be negative: {distance}"
                )

            reward = math.exp(-distance / self.distance_scale)

        # Numerical protection.
        reward = min(1.0, max(0.0, reward))

        self._distance_fitness_sum += reward
        self._fitness_tick_count += 1

    # ----------------------------------------------------------------------
    # S2 - Destroy and collect blocks
    # ----------------------------------------------------------------------

    def _update_s2(self):
        """
        S2: Destroy and collect blocks.

        +0.5  when a block is destroyed
        +0.5  when a block is collected into inventory
        -1.0  when a block is placed

        Destruction is detected by a decrease in the number of blocks
        remaining in the arena.

        Collection is detected by an increase in the agent's blue-wool
        inventory.

        Placement is detected by an increase in the number of blue-wool
        blocks in the arena.
        """

        current_arena_count = self._get_blue_wool_count()
        current_inventory_count = self._get_blue_wool_inventory_count()

        previous_arena_count = self._previous_arena_block_count
        previous_inventory_count = self._previous_inventory_count

        # --------------------------------------------------------------
        # Block destroyed
        # --------------------------------------------------------------
        destroyed = max(
            0,
            previous_arena_count - current_arena_count
        )

        self._event_fitness += destroyed * 0.5

        # --------------------------------------------------------------
        # Block collected
        # --------------------------------------------------------------
        collected = max(
            0,
            current_inventory_count - previous_inventory_count
        )

        self._event_fitness += collected * 0.5

        # --------------------------------------------------------------
        # Block placed
        # --------------------------------------------------------------
        placed = max(
            0,
            current_arena_count - previous_arena_count
        )

        self._event_fitness -= placed * 1.0

        # Store state for next tick.
        self._previous_arena_block_count = current_arena_count
        self._previous_inventory_count = current_inventory_count

    # ----------------------------------------------------------------------
    # S3 - Find current line
    # ----------------------------------------------------------------------

    def _update_s3(self):
        """
        S3: Find the currently longest line.

        Same principle as S1, but the target is the current longest line
        rather than the nearest block.

        reward = exp(-distance_to_longest_line / distance_scale)

        Maximum reward is 1.0.
        """

        distance = self.sensing.get_distance_to_longest_blue_wool_line(
            self.environment.origin,
            self.environment.size,
            block_name=BlockTypes.BLUE_WOOL
        )

        if distance is None:
            reward = 0.0
        else:
            if distance < 0:
                raise ValueError(
                    f"Distance to longest line cannot be negative: {distance}"
                )

            reward = math.exp(-distance / self.distance_scale)

        reward = min(1.0, max(0.0, reward))

        self._distance_fitness_sum += reward
        self._fitness_tick_count += 1

    # ----------------------------------------------------------------------
    # S4 - Extend current line
    # ----------------------------------------------------------------------

    def _update_s4(self):
        """
        S4: Extend the current line.

        +1  when the longest line becomes longer
        -1  for a false placement
        -1  when a correctly placed line block is destroyed

        A false placement is defined as:

            blue-wool count increases
            AND
            longest-line length does not increase

        A correctly placed block being destroyed is detected when the
        longest-line length decreases.
        """

        current_arena_count = self._get_blue_wool_count()
        current_line_length = self._get_longest_line_length()

        previous_arena_count = self._previous_arena_block_count
        previous_line_length = self._previous_longest_line_length

        # --------------------------------------------------------------
        # Correct extension
        # --------------------------------------------------------------
        line_extension = max(
            0,
            current_line_length - previous_line_length
        )

        if line_extension > 0:
            self._event_fitness += 1.0

        # --------------------------------------------------------------
        # False placement
        # --------------------------------------------------------------
        placed_blocks = max(
            0,
            current_arena_count - previous_arena_count
        )

        # For each block that did not extend the line reduce the fitness by one
        self._event_fitness -= placed_blocks - line_extension * 1.0

        # --------------------------------------------------------------
        # Correctly placed block destroyed
        # --------------------------------------------------------------
        line_destroyed = max(
            0,
            previous_line_length - current_line_length
        )

        if line_destroyed > 0:
            self._event_fitness -= line_destroyed * 1.0

        # Store state for next tick.
        self._previous_arena_block_count = current_arena_count
        self._previous_longest_line_length = current_line_length

    # ----------------------------------------------------------------------
    # Fitness helper functions
    # ----------------------------------------------------------------------

    def _get_blue_wool_count(self):
        """
        Return the number of blue-wool blocks currently present in this
        agent's arena.

        This uses the existing get_blocks_in_arena() interface from the
        experiment/environment code.
        """

        blocks = self.sensing.get_blocks_in_arena(
            self.environment.origin,
            self.environment.size,
            {self.BLUE_WOOL: 0},
        )

        return int(blocks.get(self.BLUE_WOOL, 0))

    def _get_blue_wool_inventory_count(self):
        """
        Return the number of blue-wool items currently in this agent's
        inventory.

        Assumes sensing.get_inventory() returns a dictionary such as:

            {
                "blue_wool": 3,
                ...
            }
        """
        return self.sensing.get_inventory_item_count(BlockTypes.BLUE_WOOL)


    def _get_longest_line_length(self):
        """
        Return the current length of the longest construction line.

        The actual line-detection implementation belongs to the environment.
        """

        return self.sensing.get_length_of_longest_line(
            self.environment.origin,
            self.environment.size,
            block_name=BlockTypes.BLUE_WOOL
        )

    # ----------------------------------------------------------------------
    # Final evaluation
    # ----------------------------------------------------------------------

    def evaluation(self):
        """
        Return this agent's fitness for the completed run.

        S1/S3:
            Average reward over all evaluated ticks.
            Therefore the maximum possible distance-based fitness is 1.

        S2/S4:
            Sum of event rewards/penalties.
        """

        if self.fitness_function in {"S1", "S3"}:
            if self._fitness_tick_count == 0:
                return 0.0

            fitness = (
                self._distance_fitness_sum
                / self._fitness_tick_count
            )

        else:
            fitness = self._event_fitness

        return round(float(fitness), 4)

    # ----------------------------------------------------------------------
    # Arena-level aggregation
    # ----------------------------------------------------------------------

    @staticmethod
    def arena_evaluation(agents):
        """
        Aggregate the fitness of all agents belonging to one arena.

        S1/S3:
            Average over all agents in the arena, as required.

        S2/S4:
            Sum all agent contributions because the event fitness is a
            team-level construction/collection result.
        """

        if not agents:
            return 0.0

        fitness_function = agents[0].fitness_function

        values = [agent.evaluation() for agent in agents]

        if fitness_function in {"S1", "S3"}:
            fitness = sum(values) / len(values)
        else:
            fitness = sum(values)

        return round(float(fitness), 4)
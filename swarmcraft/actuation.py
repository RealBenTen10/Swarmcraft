"""
agent actuation class
like a robot actuator suite - every agent gets one of these
"""

from javascript import require, On, Once, AsyncTask, once, off

from swarmcraft import MovementKeys

import math
import time

pathfinder = require("mineflayer-pathfinder")
goals = require("mineflayer-pathfinder/lib/goals")
Vec3 = require("vec3").Vec3


class Actuation(object):

    def __init__(self, agent):
        self.agent = agent
        self.init_pathfinder()

    ###########################################################################
    # Initialization
    ###########################################################################

    def init_pathfinder(self):
        """
        Initialize Mineflayer Pathfinder.
        This is only executed once per agent.
        """
        self.agent.bot.loadPlugin(pathfinder.pathfinder)

        self.movements = pathfinder.Movements(self.agent.bot)
        self.agent.bot.pathfinder.setMovements(self.movements)

    ###########################################################################
    # Helper functions
    ###########################################################################

    def _to_vec3(self, position):
        """
        Convert tuple/list to Vec3 if necessary.
        """
        if position is None:
            return None
        return Vec3(position[0], position[1], position[2])

    def _find_nearest_block(self,
                            block_name,
                            max_distance=32,
                            count=1):
        """
        Returns the position of the nearest block of the requested type.

        Parameters
        ----------
        block_name : str
            Minecraft block id.

        max_distance : int
            Maximum search radius.

        count : int
            Number of candidates Mineflayer should inspect.

        Returns
        -------
        Vec3 | None
        """

        try:
            # 1. Retrieve the block data from Mineflayer's registry
            block_data = self.agent.bot.registry.blocksByName[block_name]

            if not block_data:
                print(f"Block '{block_name}' not found in registry.")
                return None

            # 2. Extract the numerical ID
            block_id = block_data.id

            # 3. Find the block using the numerical ID for the matching parameter
            block = self.agent.bot.findBlock({
                "matching": block_id,
                "maxDistance": max_distance,
                "count": count
            })

            # 4. If a block was found, return its position coordinates (Vec3)
            if block is not None:
                return block

            # Return None if no matching block is within range
            return None

        except Exception as e:
            print("findBlock failed:", e)
            return None


    def _distance_to(self, position):
        """
        Euclidean distance from the bot to a position.
        """

        if position is None:
            return math.inf

        bot_pos = self.agent.bot.entity.position

        dx = bot_pos.x - position.x
        dy = bot_pos.y - position.y
        dz = bot_pos.z - position.z

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _look_at_block(self, block):
        """
        Rotate the bot to face a block.

        Returns
        -------
        bool
            True if successful.
        """

        if block is None:
            return False

        try:
            self.agent.bot.lookAt(block.position, True)
            return True

        except Exception as e:
            print("lookAt failed:", e)
            return False

    def _goal_near_block(self,
                         block,
                         distance=1):
        """
        Creates a GoalNear from a block.
        """

        if block is None:
            return None

        return goals.GoalNear(
            block.position.x,
            block.position.y,
            block.position.z,
            distance
        )

    def _goal_near_position(self,
                            position,
                            distance=1):
        """
        Creates a GoalNear from a coordinate.
        """

        position = self._to_vec3(position)

        if position is None:
            return None

        return goals.GoalNear(
            position.x,
            position.y,
            position.z,
            distance
        )

    ###########################################################################
    # Communication
    ###########################################################################

    def say(self, message: str):
        self.agent.bot.chat(message)

    def whisper(self, message: str, recipient_name: str):
        self.agent.bot.whisper(recipient_name, message)

    def send_message(self, message: str, recipient_id: str):
        self.agent.message_server.send(
            self.agent,
            message,
            recipient_id
        )

    def send_message_ranged(self,
                            message: str,
                            recipient_id: str,
                            distance: float):

        if distance < 0:
            self.send_message(message, recipient_id)
        else:
            self.agent.message_server.send(
                self.agent,
                message,
                recipient_id,
                distance
            )

    def send_global_message(self, message: str):
        self.agent.message_server.send(
            self.agent,
            message
        )

    def send_global_message_ranged(self,
                                   message: str,
                                   distance: float):

        if distance < 0:
            self.send_global_message(message)
        else:
            self.agent.message_server.send(
                self.agent,
                message,
                None,
                distance
            )

    ###########################################################################
    # Movement
    ###########################################################################

    def start_move(self, direction: str):
        """
        Start moving in a given direction.

        Direction may be one of:
        ['forward', 'back', 'left', 'right',
         'jump', 'sprint', 'sneak']
        """

        if direction not in [el.value for el in MovementKeys]:
            raise ValueError(
                f"direction must be one of {[el.value for el in MovementKeys]}"
            )

        self.agent.bot.setControlState(direction, True)

    def stop_move(self, direction: str):
        """
        Stop moving in one direction.
        """

        if direction not in [el.value for el in MovementKeys]:
            raise ValueError(
                f"direction must be one of {[el.value for el in MovementKeys]}"
            )

        self.agent.bot.setControlState(direction, False)

    def stop(self):
        """
        Stop all movement.
        """

        self.agent.bot.clearControlStates()

    ###########################################################################
    # Short movement primitives
    ###########################################################################

    def step_forward(self, ticks=8):
        """
        Small forward movement.

        Useful GP primitive because it removes the need for
        PressDir -> wait -> ReleaseDir.
        """

        self.stop()

        self.start_move("forward")

        @AsyncTask(start=True)
        def task(_):
            time.sleep(ticks / 20.0)
            self.stop()

    def step_backward(self, ticks=8):

        self.stop()

        self.start_move("back")

        @AsyncTask(start=True)
        def task(_):
            time.sleep(ticks / 20.0)
            self.stop()

    def strafe_left(self, ticks=8):

        self.stop()

        self.start_move("left")

        @AsyncTask(start=True)
        def task(_):
            time.sleep(ticks / 20.0)
            self.stop()

    def strafe_right(self, ticks=8):

        self.stop()

        self.start_move("right")

        @AsyncTask(start=True)
        def task(_):
            time.sleep(ticks / 20.0)
            self.stop()

    def jump(self):

        self.agent.bot.setControlState("jump", True)

        @AsyncTask(start=True)
        def task(_):
            time.sleep(0.2)
            self.agent.bot.setControlState("jump", False)

    ###########################################################################
    # Looking
    ###########################################################################

    def look(self, direction: tuple[float, float]):
        """
        Look in absolute yaw/pitch.
        """

        self.agent.bot.look(
            direction[0],
            direction[1],
            True
        )

    def look_at(self, position):
        """
        Look at world coordinate.
        """

        position = self._to_vec3(position)

        if position is None:
            return False

        try:
            self.agent.bot.lookAt(position, True)
            return True

        except Exception:
            return False

    def rotate(self, yaw_delta, pitch_delta=0):
        """
        Rotate relative to current heading.
        """

        yaw = self.agent.bot.entity.yaw + yaw_delta
        pitch = self.agent.bot.entity.pitch + pitch_delta

        self.agent.bot.look(
            yaw,
            pitch,
            True
        )

    ###########################################################################
    # Orientation primitives
    ###########################################################################

    def face_block_type(self,
                        block_name,
                        max_distance=32):
        """
        Look at the nearest block of a given type.
        """

        block = self._find_nearest_block(
            block_name,
            max_distance=max_distance
        )

        return self._look_at_block(block)

    def face_nearest_block(self,
                           block_name,
                           max_distance=32):
        """
        Alias kept for GP readability.
        """

        return self.face_block_type(
            block_name,
            max_distance
        )

    ###########################################################################
    # Pathfinder navigation
    ###########################################################################

    def move_to_position(self,
                         position,
                         range_goal=1):
        """
        Navigate to a coordinate.
        """

        goal = self._goal_near_position(
            position,
            range_goal
        )

        if goal is None:
            return False

        self.agent.bot.pathfinder.setGoal(goal)

        return True

    def move_to_nearest_block(self,
                              block_name,
                              range_goal=1,
                              max_distance=32):
        """
        Navigate to nearest block of the requested type.
        """

        block = self._find_nearest_block(
            block_name,
            max_distance=max_distance
        )

        if block is None:
            return False

        goal = self._goal_near_block(
            block,
            range_goal
        )

        self.agent.bot.pathfinder.setGoal(goal)

        return True

    def stop_navigation(self):
        """
        Stop Pathfinder.
        """

        self.agent.bot.pathfinder.setGoal(None)

    ###########################################################################
    # Position helpers
    ###########################################################################

    def distance_to_block(self,
                          block_name,
                          max_distance=32):
        """
        Returns distance to nearest block.
        Returns math.inf if none exists.
        """

        block = self._find_nearest_block(
            block_name,
            max_distance
        )

        if block is None:
            return math.inf

        return self._distance_to(block.position)

    ###########################################################################
    # Digging
    ###########################################################################

    def start_dig(self, block_name="blue_wool"):
        """
        Starts digging the nearest block of the requested type.

        Parameters
        ----------
        block_name : str | None

            None -> dig nearest diggable block.
            otherwise -> dig nearest block of that type.
        """

        if self.agent.bot.targetDigBlock is not None:
            return False

        try:

            if block_name is None:

                positions = self.agent.sensing.can_dig_block_in_proximity()

                if len(positions) == 0:
                    return False

                block = self.agent.bot.blockAt(positions[0])

            else:

                block = self._find_nearest_block(
                    block_name,
                    max_distance=2
                )

            if block is None:
                return False

            if not self.agent.bot.canDigBlock(block):
                return False

            self.agent.bot.dig(block)

            return True

        except Exception as e:
            print("Dig failed:", e)
            return False


    def stop_dig(self):

        if self.agent.bot.targetDigBlock is not None:
            self.agent.bot.stopDigging()


    ###########################################################################
    # Inventory
    ###########################################################################

    def select_hotbar(self, slot):

        if slot < 0 or slot > 8:
            raise ValueError("Hotbar slot must be in [0,8].")

        self.agent.bot.setQuickBarSlot(slot)


    def equip_item_type(self,
                        item_name,
                        destination="hand"):
        """
        Equip the first matching inventory item.

        destination:
            hand
            head
            torso
            legs
            feet
            off-hand
        """

        try:

            items = self.agent.bot.inventory.items()

            for item in items:

                if item.name == item_name:

                    self.agent.bot.equip(
                        item,
                        destination
                    )

                    return True

            return False

        except Exception as e:

            print("Equip failed:", e)
            return False


    def has_item(self,
                 item_name):

        try:

            for item in self.agent.bot.inventory.items():

                if item.name == item_name:
                    return True

            return False

        except Exception:

            return False


    ###########################################################################
    # Placement
    ###########################################################################

    def place_block(self,
                    face=None):
        """
        Generic Mineflayer placement.

        face:
            None -> use cursor face

            or

            (1,0,0)
            (-1,0,0)
            (0,1,0)
            (0,-1,0)
            (0,0,1)
            (0,0,-1)
        """

        if face is not None:

            if face not in [
                (1,0,0),
                (-1,0,0),
                (0,1,0),
                (0,-1,0),
                (0,0,1),
                (0,0,-1)
            ]:
                raise ValueError("Invalid placement face.")

        block = self.agent.bot.blockAtCursor()

        if block is None:
            return False

        try:

            if face is None:

                self.agent.bot.placeBlock(
                    block,
                    block.face
                )

            else:

                self.agent.bot.placeBlock(
                    block,
                    Vec3(face[0], face[1], face[2])
                )

            return True

        except Exception:

            return False


    ###########################################################################
    # Construction primitives
    ###########################################################################

    def place_forward(self):
        """
        Place block on the face currently looked at.
        """

        return self.place_block()


    def place_on_top(self):
        """
        Place block on top face.
        """

        return self.place_block((0,1,0))


    def place_underneath(self):
        """
        Place block underneath target.
        """

        return self.place_block((0,-1,0))


    def place_north(self):

        return self.place_block((0,0,-1))


    def place_south(self):

        return self.place_block((0,0,1))


    def place_east(self):

        return self.place_block((1,0,0))


    def place_west(self):

        return self.place_block((-1,0,0))


    ###########################################################################
    # Placement queries
    ###########################################################################

    def can_place_forward(self):
        """
        Checks whether a block is currently targeted.

        This is intentionally lightweight and suitable for GP.
        """

        try:

            block = self.agent.bot.blockAtCursor()

            return block is not None

        except Exception:

            return False


    ###########################################################################
    # Utility
    ###########################################################################

    def held_item_name(self):

        item = self.agent.bot.heldItem

        if item is None:
            return None

        return item.name

    ###########################################################################
    # Coordinate utilities
    ###########################################################################

    def current_position(self):
        """
        Returns the bot position as a tuple.
        """

        pos = self.agent.bot.entity.position

        return (
            pos.x,
            pos.y,
            pos.z
        )


    def current_block_position(self):
        """
        Returns the current integer block position.
        """

        pos = self.agent.bot.entity.position

        return (
            int(round(pos.x)),
            int(round(pos.y)),
            int(round(pos.z))
        )


    def heading(self):
        """
        Returns current yaw/pitch.
        """

        return (
            self.agent.bot.entity.yaw,
            self.agent.bot.entity.pitch
        )


    ###########################################################################
    # Cursor utilities
    ###########################################################################

    def cursor_block(self):
        """
        Returns the block currently looked at.
        """

        try:
            return self.agent.bot.blockAtCursor()

        except Exception:
            return None


    def cursor_block_position(self):

        block = self.cursor_block()

        if block is None:
            return None

        return block.position


    ###########################################################################
    # Relative block utilities
    ###########################################################################

    def block_at_offset(self,
                        dx,
                        dy,
                        dz):
        """
        Returns the block relative to the bot.
        """

        pos = self.agent.bot.entity.position.offset(
            dx,
            dy,
            dz
        )

        return self.agent.bot.blockAt(pos)


    def block_name_at_offset(self,
                             dx,
                             dy,
                             dz):

        block = self.block_at_offset(
            dx,
            dy,
            dz
        )

        if block is None:
            return None

        return block["name"]


    ###########################################################################
    # Pathfinder state
    ###########################################################################

    def navigation_finished(self):
        """
        Returns True when no active path exists.
        """

        try:

            return not self.agent.bot.pathfinder.isMoving()

        except Exception:

            return True


    def navigation_active(self):
        """
        Returns True while following a path.
        """

        return not self.navigation_finished()


    ###########################################################################
    # Inventory information
    ###########################################################################

    def inventory_items(self):
        """
        Returns all inventory items.
        """

        try:
            return self.agent.bot.inventory.items()

        except Exception:
            return []


    def inventory_contains(self,
                           item_name):

        for item in self.inventory_items():

            if item.name == item_name:
                return True

        return False


    ###########################################################################
    # Nearby block queries
    ###########################################################################

    def nearest_block(self,
                      block_name,
                      max_distance=32):

        return self._find_nearest_block(
            block_name,
            max_distance=max_distance
        )


    def nearest_block_position(self,
                               block_name,
                               max_distance=32):

        block = self.nearest_block(
            block_name,
            max_distance
        )

        if block is None:
            return None

        return block.position


    def nearest_block_distance(self,
                               block_name,
                               max_distance=32):

        block = self.nearest_block(
            block_name,
            max_distance
        )

        if block is None:
            return math.inf

        return self._distance_to(
            block.position
        )


    ###########################################################################
    # Relative orientation
    ###########################################################################

    def look_down(self):

        self.agent.bot.look(
            self.agent.bot.entity.yaw,
            math.pi / 2,
            True
        )


    def look_up(self):

        self.agent.bot.look(
            self.agent.bot.entity.yaw,
            -math.pi / 2,
            True
        )


    def look_forward(self):

        self.agent.bot.look(
            self.agent.bot.entity.yaw,
            0,
            True
        )
    # ------------------------------------------------------------------
    # Target acquisition
    # ------------------------------------------------------------------

    def find_nearest_block(self, block_name: str, radius: int = 16):
        """
        Returns the nearest block of the requested type.
        Wrapper around mineflayer.findBlock().
        """

        try:
            return self.agent.bot.findBlock({
                "matching": lambda block: block and block.name == block_name,
                "maxDistance": radius
            })
        except Exception:
            return None


    def find_blocks(self, block_name: str, radius: int = 16, count: int = 32):
        """
        Returns a list of matching blocks.
        """

        try:
            return self.agent.bot.findBlocks({
                "matching": lambda block: block and block.name == block_name,
                "maxDistance": radius,
                "count": count
            })
        except Exception:
            return []


    def find_nearest_placeable_surface(self, radius: int = 6):
        """
        Finds the closest solid block that can serve as support for placement.
        """

        try:
            return self.agent.bot.findBlock({
                "matching": lambda block:
                    block is not None
                    and block.boundingBox == "block",
                "maxDistance": radius
            })
        except Exception:
            return None


    # ------------------------------------------------------------------
    # Orientation
    # ------------------------------------------------------------------

    def face_block(self, block):
        """
        Rotate toward the center of a block.
        """

        if block is None:
            return False

        try:
            pos = block.position.offset(0.5, 0.5, 0.5)
            self.agent.bot.lookAt(pos, True)
            return True
        except Exception:
            return False


    def face_position(self, position):
        """
        Face an arbitrary world coordinate.
        """

        if position is None:
            return False

        try:
            self.agent.bot.lookAt(
                Vec3(position[0], position[1], position[2]),
                True
            )
            return True
        except Exception:
            return False



    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def move_to_block(self,
                      block_name: str,
                      radius: int = 32,
                      goal_distance: int = 1):
        """
        Navigate toward the closest matching block.
        """

        block = self.find_nearest_block(block_name, radius)

        if block is None:
            return False

        pos = block.position

        self.agent.bot.pathfinder.setGoal(
            pathfinder.goals.GoalNear(
                pos.x,
                pos.y,
                pos.z,
                goal_distance
            )
        )

        return True



    def is_navigation_finished(self):
        """
        True if no active goal exists.
        """

        return self.agent.bot.pathfinder.goal is None


    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------

    def place_against_block(self,
                            support_block,
                            face=(0, 1, 0)):
        """
        Place currently held block against a specific support block.
        """

        if support_block is None:
            return False

        try:
            self.agent.bot.placeBlock(
                support_block,
                Vec3(face[0], face[1], face[2])
            )
            return True
        except Exception:
            return False


    def place_block_forward(self):
        """
        Place a block directly in front of the agent.

        Uses the currently looked-at block as support.
        """

        try:

            support = self.agent.bot.blockAtCursor()

            if support is None:
                return False

            self.agent.bot.placeBlock(
                support,
                support.face
            )

            return True

        except Exception:
            return False


    def place_block_on_top(self):
        """
        Place a block on top of the currently looked-at block.
        """

        try:

            support = self.agent.bot.blockAtCursor()

            if support is None:
                return False

            self.agent.bot.placeBlock(
                support,
                Vec3(0, 1, 0)
            )

            return True

        except Exception:
            return False

    def equip_placeable_block(self) -> bool:
        """
        Ensures the bot is holding a placeable block. Equips the first
        valid block from the inventory if not currently holding one.
        """
        registry_blocks = self.agent.bot.registry.blocksByName
        held = self.agent.bot.heldItem

        if held is not None and held.name in registry_blocks:
            return True

        for item in self.agent.bot.inventory.items():
            if item is not None and item.name in registry_blocks:
                try:
                    self.agent.bot.equip(item, "hand")
                    return True
                except Exception as e:
                    print("Equip failed:", e)
                    return False

        return False

    def place_block_in_front(self) -> bool:
        """
        Places a block in front of the agent by attaching it to the top
        face of the support block directly beneath the target position.

        The support position must contain a non-air block, and the target
        position itself must be air.
        """
        if not self.equip_placeable_block():
            return False

        yaw, _ = self.heading()
        off_x = int(round(-math.sin(yaw)))
        off_z = int(round(math.cos(yaw)))

        # Target position in front of the agent
        front_pos = self.agent.bot.entity.position.offset(off_x, 0, off_z)

        # Block that should be placed at the target position
        target_block = self.agent.bot.blockAt(front_pos)

        # Target position must be air
        if target_block is None or target_block.name != "air":
            return False

        # Support block directly beneath the target position
        support_pos = front_pos.offset(0, -1, 0)
        support_block = self.agent.bot.blockAt(support_pos)

        # Support block must exist and must not be air
        if support_block is None or support_block.name == "air":
            return False

        try:
            # Place the equipped block on the top face of the support block
            self.agent.bot.placeBlock(support_block, Vec3(0, 1, 0))
            return True
        except Exception as e:
            print("place_block_in_front failed:", e)
            return False

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    def equip_item(self, item_name: str):
        """
        Equip the first inventory item matching item_name.
        """

        try:

            for item in self.agent.bot.inventory.items():

                if item.name == item_name:

                    self.agent.bot.equip(
                        item,
                        "hand"
                    )

                    return True

            return False

        except Exception:
            return False

# forage environment initializes with a couple randomly-placed, randomly-sized
# 2-high blocks of diamond
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

    @override
    def reset(self):
        """Resets the environment
        Clears all blocks"""
        self.minecraft_server.send(f'setcube {self.origin[0]} {self.origin[1]} {self.origin[2]} {self.size[0]} {self.size[1]} {self.size[2]} minecraft:{BlockTypes.AIR.value}')

    @override
    def initialize(self):
        self.minecraft_server.send(
            f'setcube {self.origin[0]} {self.origin[1]} {self.origin[2]} {self.size[0]} {1} {self.size[2]} minecraft:{BlockTypes.BEDROCK.value}')
        for x in range(self.size[0]):
            for y in range(self.size[2]):
                if x == 0 or x == self.size[0] - 1 or y == 0 or y == self.size[2] - 1:
                    pos = add_tuples(self.origin, (x, 1, y))
                    self.minecraft_server.send(
                        f'setblock {pos[0]} {pos[1]} {pos[2]} minecraft:{BlockTypes.BEDROCK.value}')
                    self.minecraft_server.send(
                        f'setblock {pos[0]} {pos[1] + 1} {pos[2]} minecraft:{BlockTypes.BEDROCK.value}')


    def set_blocks(self, blocks = {'blue_wool': 4,'orange_wool': 4,'brown_wool': 0,'green_wool': 0}):
        """Spawns wool blocks within the bedrock perimeter at unique locations"""

        self.blocks = blocks

        occupied_coords = set()
        center_x = self.origin[0] + self.size[0] // 2
        center_z = self.origin[2] + self.size[2] // 2
        occupied_coords.add((center_x, self.origin[1] + 1, center_z))

        for block_type, count in self.blocks.items():
            for _ in range(count):
                while True:
                    # 1. Generate candidate coordinates inside the arena
                    x_pos = random.randint(self.origin[0] + 1, self.origin[0] + self.size[0] - 2)
                    z_pos = random.randint(self.origin[2] + 1, self.origin[2] + self.size[2] - 2)
                    y_pos = self.origin[1] + 1

                    coord = (x_pos, y_pos, z_pos)

                    # 2. Check if this spot is already taken by another wool block
                    if coord not in occupied_coords:
                        # 3. Mark as occupied and send the command
                        occupied_coords.add(coord)
                        self.minecraft_server.send(
                            f'setblock {x_pos} {y_pos} {z_pos} minecraft:{block_type}'
                        )
                        break


    def get_point_in_environment(self):
        return random.randint(self.origin[0] + 1, self.origin[0] + self.size[0]), self.origin[1] + 1, random.randint(self.origin[2] + 1, self.origin[2] + self.size[2])

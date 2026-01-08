# forage environment initializes with a couple randomly-placed, randomly-sized
# 2-high blocks of diamond
import random
from typing import override

from swarmcraft.environment import Environment
from swarmcraft.util import add_tuples
from swarmcraft import BlockTypes

START_LOCATION = (20, -57, 20)
class ForageEnvironment(Environment):
    def __init__(self, minecraft_server, origin: tuple[int, int, int]=(0, -60, 0), size: tuple[int, int, int]=(20, 10, 20),
                 resource_min_size=1, resource_max_size=2, resource_count=1):
        super().__init__(minecraft_server, origin, size)
        self.resource_min_size = resource_min_size
        self.resource_max_size = resource_max_size
        self.resource_count = resource_count
        self.resource_positions = []
        self.blocks = None

    @override
    def initialize(self):
        super().initialize()
        #self.resource_positions = []
        # generate the resource chunks
        '''
        for _ in range(self.resource_count):
            w = random.randint(self.resource_min_size, self.resource_max_size)
            x_off = random.randint(1, self.size[0] - 2)
            y_off = random.randint(1, self.size[2] - 2)
            for x in range(w):
                for y in range(w):
                    b_pos = add_tuples(self.origin, (x + x_off, 0, y + y_off))
                    if self.origin[0] + self.size[0] - 1 > b_pos[0] > self.origin[0] + 1 and self.origin[2] + self.size[2] - 1 > \
                            b_pos[2] > self.origin[2] + 1:
                        self.minecraft_server.send(f'setblock {b_pos[0]} {b_pos[1]} {b_pos[2]} minecraft:{BlockTypes.ORANGE_WOOL.value}')
                        self.resource_positions.append(b_pos)
        '''

    def set_blocks(self, blocks = {'blue_wool': 4,'orange_wool': 4,'brown_wool': 0,'green_wool': 0}):
        """Spawns wool blocks within the bedrock perimeter at unique locations"""
        # TODO
        # Move the random generation of positions to another function
        # It should be possible to use the same environment 2+ times
        self.blocks = blocks

        occupied_coords = set()
        occupied_coords.add((20, self.origin[1] + 1, 20))

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

# forage environment initializes with a couple randomly-placed, randomly-sized
# 2-high blocks of diamond
import random
from typing import override

from swarmcraft.environment import Environment
from swarmcraft.util import add_tuples
from swarmcraft import BlockTypes

START_LOCATION = (20, -55, 20)
class ForageEnvironment(Environment):
    def __init__(self, minecraft_server, origin: tuple[int, int, int]=(0, -60, 0), size: tuple[int, int, int]=(100, 100, 100),
                 resource_min_size=1, resource_max_size=2, resource_count=1):
        super().__init__(minecraft_server, origin, size)
        self.resource_min_size = resource_min_size
        self.resource_max_size = resource_max_size
        self.resource_count = resource_count
        self.resource_positions = []

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
        # Create Blocks around agent for dig
        for j in range(1,5):
            for i in range(1,2):
                self.minecraft_server.send(
                f'setblock {START_LOCATION[0]+j} {self.origin[1] + i} {START_LOCATION[2]} minecraft:{BlockTypes.BLUE_WOOL.value}')
                self.minecraft_server.send(
                    f'setblock {START_LOCATION[0] - j} {self.origin[1] + i} {START_LOCATION[2]} minecraft:{BlockTypes.BLUE_WOOL.value}')
                self.minecraft_server.send(
                f'setblock {START_LOCATION[0]} {self.origin[1] + i} {START_LOCATION[2]+j} minecraft:{BlockTypes.BLUE_WOOL.value}')
                self.minecraft_server.send(
                    f'setblock {START_LOCATION[0]} {self.origin[1] + i} {START_LOCATION[2]-j} minecraft:{BlockTypes.BLUE_WOOL.value}')

    def get_point_in_environment(self):
        return random.randint(self.origin[0] + 1, self.origin[0] + self.size[0]), self.origin[1] + 1, random.randint(self.origin[2] + 1, self.origin[2] + self.size[2])

# forage environment initializes with a couple randomly-placed, randomly-sized
# 2-high blocks of diamond
import random
from typing import override

from test_evocraft_py import DIAMOND_BLOCK

from server.minecraft_server import minecraft_server
from environments.environment import Environment
from util import add_tuples
from server.pooler import WORLD_CENTER


class ForageEnvironment(Environment):
    def __init__(self, origin: tuple[int, int, int]=WORLD_CENTER, size: tuple[int, int, int]=(100, 100, 100),
                 resource_min_size=1, resource_max_size=2, resource_count=1):
        super().__init__(origin, size)
        self.resource_min_size = resource_min_size
        self.resource_max_size = resource_max_size
        self.resource_count = resource_count

    @override
    def initialize(self):
        super().initialize()
        # generate the resource chunks
        blocks = []
        positions = []
        for _ in range(self.resource_count):
            w = random.randint(self.resource_min_size, self.resource_max_size)
            x_off = random.randint(1, self.size[0] - 2)
            y_off = random.randint(1, self.size[2] - 2)
            for x in range(w):
                for y in range(w):
                    b_pos = add_tuples(self.origin, (x + x_off, 1, y + y_off))
                    if self.origin[0] + self.size[0] - 1 > b_pos[0] > self.origin[0] + 1 and self.origin[2] + self.size[2] - 1 > \
                            b_pos[2] > self.origin[2] + 1:
                        blocks.append(DIAMOND_BLOCK)
                        positions.append(b_pos)
        minecraft_server.spawn_blocks(positions, blocks)

    def get_point_in_environment(self):
        return random.randint(self.origin[0] + 1, self.size[0] - 1), self.origin[1] + 1, random.randint(self.origin[2] + 1, self.size[2] - 1)

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
                 resource_min_size=5, resource_max_size=10, resource_count=1):
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
            h = random.randint(self.resource_min_size, self.resource_max_size)
            x_off = random.randint(1, self.size[0] - 2)
            y_off = random.randint(1, self.size[2] - 2)
            for x in range(w):
                for y in range(h):
                    blocks.append(DIAMOND_BLOCK)
                    positions.append(add_tuples(self.origin, (x + x_off, 1, y + y_off)))
                    blocks.append(DIAMOND_BLOCK)
                    positions.append(add_tuples(self.origin, (x + x_off, 2, y + y_off)))
        minecraft_server.spawn_blocks(positions, blocks)

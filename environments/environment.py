from typing import override

from mazelib import Maze
from mazelib.generate.Wilsons import Wilsons
from test_evocraft_py import AIR, GRASS, BRICK_BLOCK, DIAMOND_BLOCK, GOLD_BLOCK, FENCE

from util import add_tuples
from world_interface.pooler import WORLD_CENTER, pooler
from server import server


class Environment(object):
    def __init__(self, origin: tuple[int, int, int]=WORLD_CENTER, size: tuple[int, int, int]=(20, 20, 20)):
        self.origin = origin
        self.size = size

    # reset the environment
    # by default, clears all blocks and spawns a ground plane at the bottom of the environment
    def reset(self):
        server.fill_cube(self.origin, add_tuples(add_tuples(self.origin, self.size), (-1, -1, -1)), AIR)
        server.fill_cube(self.origin, (self.origin[0] + self.size[0] - 1, self.origin[1], self.origin[2] + self.size[2] - 1), GRASS)

    # set the environment to an initial state
    # by default just builds a fence around the edge
    def initialize(self):
        blocks = []
        positions = []
        for x in range(self.size[0]):
            for y in range(self.size[2]):
                if x == 0 or x == self.size[0] - 1 or y == 0 or y == self.size[2] - 1:
                    blocks.append(FENCE)
                    positions.append(add_tuples(self.origin, (x, 1, y)))
        server.spawn_blocks(positions, blocks)

# example maze environment
class MazeEnv(Environment):
    def __init__(self, origin: tuple[int, int, int]=WORLD_CENTER, size: tuple[int, int, int]=(20, 20, 20)):
        super().__init__(origin, size)
        self.entrance = None
        self.exit = None

    @override
    def initialize(self):
        m = Maze()
        # sizing is weird
        # odd environment sizes deliver mazes which fill the space
        # even environment sizes deliver mazes which leave a gap
        # seems to be a peculiarity of mazelib
        w = int((self.size[0] - (1 if self.size[0] % 2 != 0 else 0)) / 2) - (1 if self.size[0] % 2 == 0 else 0)
        h = int((self.size[2] - (1 if self.size[2] % 2 != 0 else 0)) / 2) - (1 if self.size[2] % 2 == 0 else 0)
        m.generator = Wilsons(w, h)
        m.generate()
        m.generate_entrances()
        print(m)
        blocks = []
        positions = []
        for x in range(len(m.grid)):
            for y in range(len(m.grid[x])):
                if m.grid[x][y] == 1:
                    blocks.extend([BRICK_BLOCK, BRICK_BLOCK])
                else:
                    blocks.extend([AIR, AIR])
                positions.extend([add_tuples(self.origin, (x, 1, y)), add_tuples(self.origin, (x, 2, y))])
        blocks.extend([GOLD_BLOCK, AIR, AIR, DIAMOND_BLOCK, AIR, AIR])
        positions.extend([
            add_tuples(self.origin, (m.start[0], 0, m.start[1])),
            add_tuples(self.origin, (m.start[0], 1, m.start[1])),
            add_tuples(self.origin, (m.start[0], 2, m.start[1])),
            add_tuples(self.origin, (m.end[0], 0, m.end[1])),
            add_tuples(self.origin, (m.end[0], 1, m.end[1])),
            add_tuples(self.origin, (m.end[0], 2, m.end[1])),
        ])
        self.entrance = add_tuples(self.origin, (m.start[0], 1, m.start[1]))
        self.exit = add_tuples(self.origin, (m.end[0], 1, m.end[1]))
        server.spawn_blocks(positions, blocks)
        pooler.activate_agent(init_location=self.entrance)

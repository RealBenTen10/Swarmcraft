from typing import override

from mazelib import Maze
from mazelib.generate.Wilsons import Wilsons

from util import add_tuples
from server.minecraft_server import minecraft_server


class Environment(object):
    def __init__(self, origin: tuple[int, int, int], size: tuple[int, int, int]):
        self.origin = origin
        self.size = size

    # reset the environment
    # by default, clears all blocks and spawns a ground plane at the bottom of the environment
    def reset(self):
        """Resets the environment
        Clears all blocks"""
        minecraft_server.fill_cube(self.origin, self.size, 'air')

    # set the environment to an initial state
    # by default just builds a fence around the edge
    def initialize(self):
        """Set the environment to an initial state
        Builds a fence around the edge and spawns a ground plane at the bottom"""
        minecraft_server.fill_cube(self.origin, (self.size[0], 0, self.size[2]), 'grass')
        for x in range(self.size[0]):
            for y in range(self.size[2]):
                if x == 0 or x == self.size[0] - 1 or y == 0 or y == self.size[2] - 1:
                    minecraft_server.spawn_block(add_tuples(self.origin, (x, 1, y)), 'fence')

# example maze environment
class MazeEnv(Environment):
    def __init__(self, origin: tuple[int, int, int], size: tuple[int, int, int]):
        super().__init__(origin, size)
        self.entrance = None
        self.exit = None

    @override
    def initialize(self):
        super().initialize()
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
        for x in range(len(m.grid)):
            for y in range(len(m.grid[x])):
                if m.grid[x][y] == 1:
                    minecraft_server.spawn_block(add_tuples(self.origin, (x, 1, y)), 'brick_block')
                    minecraft_server.spawn_block(add_tuples(self.origin, (x, 2, y)), 'brick_block')
                else:
                    minecraft_server.spawn_block(add_tuples(self.origin, (x, 1, y)), 'air')
                    minecraft_server.spawn_block(add_tuples(self.origin, (x, 2, y)), 'air')
        minecraft_server.spawn_block(add_tuples(self.origin, (m.start[0], 0, m.start[1])), 'gold_block')
        minecraft_server.spawn_block(add_tuples(self.origin, (m.start[0], 1, m.start[1])), 'air')
        minecraft_server.spawn_block(add_tuples(self.origin, (m.start[0], 2, m.start[1])), 'air')
        minecraft_server.spawn_block(add_tuples(self.origin, (m.end[0], 0, m.end[1])), 'diamond_block')
        minecraft_server.spawn_block(add_tuples(self.origin, (m.end[0], 1, m.end[1])), 'air')
        minecraft_server.spawn_block(add_tuples(self.origin, (m.end[0], 2, m.end[1])), 'air')
        self.entrance = add_tuples(self.origin, (m.start[0], 1, m.start[1]))
        self.exit = add_tuples(self.origin, (m.end[0], 1, m.end[1]))

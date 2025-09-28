from swarmcraft.minecraft.server import MinecraftServer
from swarmcraft.util import add_tuples
from swarmcraft import BLOCK_TYPES

class Environment(object):
    def __init__(self, minecraft_server: MinecraftServer, origin: tuple[int, int, int], size: tuple[int, int, int]):
        self.origin = origin
        self.size = size
        self.minecraft_server = minecraft_server

    def reset(self):
        """Resets the environment
        Clears all blocks"""
        self.minecraft_server.send(f'setcube {self.origin[0]} {self.origin[1]} {self.origin[2]} {self.size[0]} {self.size[1]} {self.size[2]} minecraft:{BLOCK_TYPES.AIR.value}')

    def log(self) -> dict:
        return {}

    def initialize(self):
        """Set the environment to an initial state
        Builds a fence around the edge and spawns a ground plane at the bottom"""
        self.minecraft_server.send(f'setcube {self.origin[0]} {self.origin[1]} {self.origin[2]} {self.size[0]} {1} {self.size[2]} minecraft:{BLOCK_TYPES.BEDROCK.value}')
        for x in range(self.size[0]):
            for y in range(self.size[2]):
                if x == 0 or x == self.size[0] - 1 or y == 0 or y == self.size[2] - 1:
                    pos = add_tuples(self.origin, (x, 1, y))
                    self.minecraft_server.send(f'setblock {pos[0]} {pos[1]} {pos[2]} minecraft:{BLOCK_TYPES.BEDROCK.value}')
                    self.minecraft_server.send(f'setblock {pos[0]} {pos[1] + 1} {pos[2]} minecraft:{BLOCK_TYPES.BEDROCK.value}')

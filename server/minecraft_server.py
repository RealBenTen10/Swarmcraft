"""
interface for starting/stopping the minecraft server
test_evocraft_py does provide functionality for this, but they don't let you hook into io streams
having the streams is nice because it lets you send server commands from the console

also initializes and provides the evocraft-py client
as well as wrappers for the latter's fillcubes and spawnblocks methods

also handles server logging
generates two logfiles:
- one for the server console (commands sent and output generated)
    - this is just a text file with each command/output timestamped on its own line
- one for blocks on the server
    - the block log consists of two portions:
        - a compressed snapshot of the server's region folder (containing all the .mca files)
"""
import os
import warnings
import subprocess
from threading import Thread
from queue import Queue, Empty

import grpc
from mcrcon import MCRcon, MCRconException
from test_evocraft_py import minecraft_pb2_grpc, FillCubeRequest, Point, Cube, AIR, BlockType, Blocks, NORTH, Block


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


class MinecraftServer:
    def __init__(self):
        self.log_dir_path = 'logs'
        self.svproc = None
        self.running = False
        self.evocraft_client = None
        self.server_output_queue = Queue()

        self.mcr = MCRcon('127.0.0.1', 'changeme')

    def start(self):
        if self.running:
            warnings.warn("Server is already running")
            return
        print("Starting server")
        # while test_evocraft_py does provide its own startup/shutdown methods, starting the server this way lets
        # me hook into the io streams
        self.svproc = subprocess.Popen(['java', '-jar', 'server.jar', 'nogui'],
                                       cwd=os.path.join(os.getcwd(), 'server'),
                                       stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        print("Started server process")
        self.running = True
        # need a loop here to check if the server is up
        # this is pretty ugly
        # must be a better way!
        while True:
            line = self.svproc.stdout.readline()
            line = line.decode()
            print(line, end='')
            if line and line.find('RCON running') != -1:
                break
            elif line and (line.find('Failed to start the minecraft server') != -1 or line.find('Stopping server') != -1):
                self.stop()
                exit(1)
        self.mcr.connect()
        print("rcon connection is up")

    # this should really get registered to an exit handler
    def stop(self):
        if not self.running:
            warnings.warn("Server is already stopped")
            return
        try: self.send_command('say got call to stop from console, going down NOW!')
        except MCRconException: pass
        self.svproc.terminate() # stop the process
        self.svproc.stdin.close() # and close its associated streams
        self.svproc.stdout.close()
        self.mcr.disconnect()
        self.running = False
        print("server stopped")

    # how to get stuff back out of here??
    # somehow svproc.stdout.read
    # what if more than one line?
    def send_command(self, command: str):
        if not self.running:
            warnings.warn("Server is not running")
            return
        return self.mcr.command(command)
'''
    def fill_cube(self, origin: tuple[float, float, float], corner: tuple[float, float, float], block: BlockType):
        self.evocraft_client.fillCube(FillCubeRequest(
            cube=Cube(
                min=Point(x=origin[0], y=origin[1], z=origin[2]),
                max=Point(x=corner[0], y=corner[1], z=corner[2]),
            ),
            type=block
        ))

    def spawn_block(self, pos: tuple[float, float, float], block: BlockType, orientation=NORTH):
        self.evocraft_client.spawnBlocks(Blocks(blocks=[
            Block(position=Point(x=pos[0], y=pos[1], z=pos[2]), type=block, orientation=orientation)
        ]))

    # this is fast.
    # if you're spawning many things at once, best use this
    def spawn_blocks(self, positions: list[tuple[float, float, float]], blocks: list[BlockType], orientations: list[int]=None):
        b = []
        if orientations is None:
            orientations = [NORTH] * len(positions)
        for pos, block, orientation in zip(positions, blocks, orientations):
            b.append(Block(position=Point(x=pos[0], y=pos[1], z=pos[2]), type=block, orientation=orientation))
        self.evocraft_client.spawnBlocks(Blocks(blocks=b))

    def read_cube(self, pos: tuple[float, float, float], corner: tuple[float, float, float]):
        return self.evocraft_client.readCube(Cube(min=Point(x=pos[0], y=pos[1], z=pos[2]),
                                    max=Point(x=corner[0], y=corner[1], z=corner[2]),
                                    ))

    def read_block(self, pos: tuple[float, float, float]):
        return self.evocraft_client.readCube(Cube(min=Point(x=pos[0], y=pos[1], z=pos[2]), max=Point(x=pos[0], y=pos[1], z=pos[2])))
'''
minecraft_server = MinecraftServer()

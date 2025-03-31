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
import math
import os
import warnings
import subprocess
from queue import Queue, Empty

from mcrcon import MCRcon, MCRconException


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

    def spawn_block(self, pos: tuple[float, float, float], block_id: str = 'stone'):
        return self.mcr.command(f'setblock {pos[0]} {pos[1]} {pos[2]} {block_id}')

    # so chunk the input volume into smaller ones
    def fill_cube(self, origin: tuple[float, float, float], size: tuple[float, float, float], block_id: str = 'stone'):
        process = [(origin, size)] # origins, sizes
        while len(process) != 0:
            o, s = process.pop() # volume origin, volume size
            vol_size = s[0] * s[1] * s[2] # calculate the volume's size
            if vol_size > 32768 or any(s_ < 0 for s_ in s): # if it's too big or any values were negative, halve it along its largest axis and append resulting volumes to the process queue
                # split the volume along its largest axis into two new volumes
                # append those to the volume queue
                greatest_index = s.index(max(s))
                first_size = list(s)
                second_size = list(s)
                second_origin = list(o)
                first_size[greatest_index] = int(math.ceil(s[greatest_index] / 2)) # size of the first block
                second_size[greatest_index] = int(math.floor(s[greatest_index] / 2)) # size of the second block
                second_origin[greatest_index] = int(o[greatest_index] + first_size[greatest_index]) # origin of the second block
                first_block = (o, tuple(first_size))
                second_block = (second_origin, tuple(second_size))
                # then the other half is all components of the old volume, except along the axis we split at - there we take
                process.append(first_block)
                process.append(second_block)
            else: # if it isn't too big, fill it
                print(f'fill {o[0]} {o[1]} {o[2]} {o[0] + s[0]} {o[1] + s[1]} {o[2] + s[2]} {block_id}')
                self.mcr.command(f'fill {o[0]} {o[1]} {o[2]} {o[0] + s[0]} {o[1] + s[1]} {o[2] + s[2]} {block_id}')

minecraft_server = MinecraftServer()

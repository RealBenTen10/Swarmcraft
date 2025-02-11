import asyncio.subprocess
import signal
import sys
import warnings
from subprocess import PIPE
from types import NoneType

running = False

class Server:
    def __init__(self):
        self.executablepath = '/home/moltmanns/Documents/swarmcraft/Evocraft-py/spongevanilla-1.12.2-7.3.0.jar'
        self.svproc = None
        self.running = False

    async def start(self):
        if self.running:
            warnings.warn("Server is already running")
            return
        print("Starting server")
        self.svproc = await asyncio.subprocess.create_subprocess_exec('java',
                                                                      '-jar', 'spongevanilla-1.12.2-7.3.0.jar',
                                                                      cwd='/home/moltmanns/Documents/swarmcraft/Evocraft-py',
                                                                      stdout=asyncio.subprocess.PIPE, stderr=sys.stderr, stdin=asyncio.subprocess.PIPE)
        # need a loop here to check if the server is up
        while True:
            line = await self.svproc.stdout.readline()
            line = line.decode()
            if line and line.find('Done') != -1:
                print(line)
                break
        self.running = True
        print("Server started")

    def stop(self):
        if not self.running:
            warnings.warn("Server is already stopped")
            return
        self.svproc.send_signal(signal.SIGINT)
        self.svproc.wait()
        self.running = False

    def send_command(self, command: str):
        if not self.running:
            warnings.warn("Server is not running")
            return
        self.svproc.stdin.write(f'{command}\n'.encode())
        #self.svproc.stdin.flush()

server = Server()

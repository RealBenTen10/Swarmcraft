import os
import sys
import warnings
import subprocess

import grpc
from test_evocraft_py import minecraft_pb2_grpc, start_server_interactive

class Server:
    def __init__(self):
        self.executablepath = '/home/moltmanns/Documents/swarmcraft/Evocraft-py/spongevanilla-1.12.2-7.3.0.jar'
        self.svproc = None
        self.running = False
        self.evocraft_client = None

    def start(self):
        if self.running:
            warnings.warn("Server is already running")
            return
        print("Starting server")
        # while test_evocraft_py does provide its own startup/shutdown methods, starting the server this way lets
        # me hook into the io streams
        self.svproc = subprocess.Popen(['java', '-jar', 'spongevanilla-1.12.2-7.3.0.jar'],
                                       cwd=os.path.join(os.getcwd(), '.venv/lib/python3.13/site-packages/test_evocraft_py/data'),
                                       stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Started server process")
        # need a loop here to check if the server is up
        while True:
            line = self.svproc.stdout.readline()
            line = line.decode()
            print(line)
            if line and line.find('Done') != -1:
                break
            elif line and line.find('Stopping server') != -1:
                self.stop()
                exit(1)
        self.running = True
        print("Server started")
        print("Attaching evocraft client")
        channel = grpc.insecure_channel('localhost:5001')
        self.evocraft_client = minecraft_pb2_grpc.MinecraftServiceStub(channel)
        print("Evocraft client attached")

    # this should really get registered to an exit handler
    def stop(self):
        if not self.running:
            warnings.warn("Server is already stopped")
            return
        self.send_command('say got call to stop from console, going down NOW!')
        self.svproc.terminate() # stop the process
        self.svproc.stdin.close() # and close its associated streams
        self.svproc.stdout.close()
        self.svproc.stderr.close()
        self.running = False
        self.svproc = None
        self.evocraft_client = None
        print("server stopped")

    def send_command(self, command: str):
        if not self.running:
            warnings.warn("Server is not running")
            return
        self.svproc.stdin.write(f'{command}\n'.encode())
        self.svproc.stdin.flush()

server = Server()

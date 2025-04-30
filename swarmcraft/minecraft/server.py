import os
import socket
import time
import warnings
import subprocess
from queue import Queue

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

HOST = '0.0.0.0'
PORT = 25576
TIMEOUT = 120 # this is probably excessive, but on slower machines startup can really take a while!

class MinecraftServer:
    def __init__(self):
        self.svproc = None # minecraft server process
        self.running = False # are we running?
        self.cmdsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # socket through which to send commands to the server
        self.server_output_queue = Queue()
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.executable_path = os.path.join(self.dir, 'spigot-1.21.1.jar')

    def start(self):
        if self.running:
            warnings.warn("Server is already running")
            return
        print("Starting spigot")
        # start spigot
        # this will also start up the command server socket (at 0.0.0.0:25576)
        self.svproc = subprocess.Popen(['java', '-jar', self.executable_path],
                                       cwd=self.dir,
                                       stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        self.running = True
        print("Connecting to command server (at %s:%d)" % (HOST, PORT))
        start = time.time()
        while True:
            try:
                if time.time() - start > TIMEOUT:
                    print("Unable to connect to server. Perhaps another instance of spigot is already running? (try 'pgrep java')")
                    self.svproc.terminate()
                    self.svproc.stdin.close()
                    self.running = False
                    return False
                self.cmdsock.connect((HOST, PORT))
            except socket.error as e:
                continue
            break
        return True

    # this should really get registered to an exit handler
    def stop(self):
        if not self.running:
            warnings.warn("Server is already stopped")
            return
        #try:
        self.send('command say got call to stop from console, going down NOW!')
        self.svproc.terminate() # stop the process
        self.svproc.stdin.close() # and close its associated streams
        self.running = False
        print("server stopped")

    """
    see plugins/PySpigot/scripts/methods.py for a list of available commands
    """
    def send(self, command: str):
        if not self.running:
            warnings.warn("Server is not running")
            return None

        header = len(command).to_bytes(2, byteorder='big', signed=False)
        self.cmdsock.send(header + command.encode('utf-8'))
        data = b''
        count = 0
        while count < 2:
            piece = self.cmdsock.recv(2)
            if not piece:
                self.cmdsock.close()
                return None
            data += piece
            count += len(piece)
        length = int.from_bytes(data, byteorder='big', signed=False)
        return self.cmdsock.recv(length).decode('utf-8')

import random
import socket
from time import sleep


def encode(msg: str):
    header = len(msg).to_bytes(2, byteorder='big', signed=False)
    return header + msg.encode('utf-8')

def receive(s):
    data = b''
    count = 0
    while count < 2:
        piece = s.recv(2)
        if not piece:
            s.close()
            return None
        data += piece
        count += len(piece)
    length = int.from_bytes(data, byteorder='big', signed=False)
    return s.recv(length).decode('utf-8')

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect(('0.0.0.0', 25576))
s.send(encode("getblocks x 10 10 y 4 5 z 10 10"))
print(receive(s))
s.send(encode("setblocks x 10 10 y 4 5 z 10 10 id diamond_block diamond_block"))
print(receive(s))
s.close()

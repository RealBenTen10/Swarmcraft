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
s.send(encode("this command is pretty super long. in fact, it's even super mega long!"))
print(receive(s))
s.send(encode("getblock 10 4 10"))
print(receive(s))
s.send(encode("setblock 10 5 10 gold_block"))
print(receive(s))
while True:
    sleep(random.random() * 2)
    s.send(encode('ping'))
    print(receive(s))
s.close()

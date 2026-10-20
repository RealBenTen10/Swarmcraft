import socket
import struct
import pyspigot as ps
import methods

# remember jython is only python 2!

HOST, PORT = '0.0.0.0', 25577

def encode(msg):
    header = struct.pack('>H', len(msg))
    return header + msg.encode('utf-8')

def handle(conn, addr):
    print("Got a connection from %s" % str(addr))
    while True:
        # get the header (first 2 bytes)
        data = b''
        count = 0
        while count < 2:
            piece = conn.recv(2)
            # if we couldn't get anything, the client must have ended the connection
            if not piece:
                conn.close()
                return
            data += piece
            count += len(piece)
        try:
            length = struct.unpack('>H', data) # unpack bytestring into a big-endian unsigned short
        except struct.error as e:
            print(e)
            conn.send(encode('ERROR (INTERNAL) check server console for more information'))
            continue

        # get the command
        # commands are split along spaces
        payload = conn.recv(length).decode('utf-8')
        spl = payload.split(' ')
        cmd = spl[0]
        args = spl[1:]
        #print("%s: %s" % (addr, payload))
        # process the command
        try:
            conn.send(encode(str(getattr(methods, cmd)(*args)))) # look up any function with the name sent in the local symbol table and run it
        except Exception as e:
            print('ERROR Command "' + cmd + '" failed. (' + str(e) + ')')
            conn.send(encode('ERROR (INTERNAL) check server console for more information'))
            continue

def wait_for_client(sock):
    sock.bind((HOST, PORT))
    sock.listen(1)
    while True:
        print("Swarmcraft endpoint listening at %s:%d" % (HOST, PORT))
        c, a = sock.accept()
        handle(c, a)
        print("%s disconnected" % str(a))
        c.close()

# doesn't run if the script crashes! (but otherwise is called on exit)
def stop():
    ps.scheduler.stopTask(t)
    s.close()
    print("Swarmcraft endpoint stopped")

# run the handler asynchronously
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
t = ps.scheduler.runTaskAsync(wait_for_client, s)

"""
Define server methods here
These will all be called asynchronously to the main server thread, so you can take your time here
Return values will be cast to a string and sent back to the client
If you do need to run things in a new (or sync) thread, use the pyspigot scheduler
"""

import pyspigot as ps
from org.bukkit import Bukkit, Location, Material

world = Bukkit.getWorld('world')

def ping(*args):
    return 'pong'

# get the block at a given coordinate
def getblock(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z).getBlockData().getAsString()
    return str(b)

# something like:
# getblocks x 10 10 10 y 2 4 5 z -3 4 4
def getblocks(*args):
    xs = []
    ys = []
    zs = []
    state = ''
    for a in args:
        if a == 'x' or a == 'y' or a == 'z':
            state = a
        elif state == 'x':
            xs.append(int(a))
        elif state == 'y':
            ys.append(int(a))
        elif state == 'z':
            zs.append(int(a))
    res = []
    for x, y, z in zip(xs, ys, zs):
        res.append({'pos': (x, y, z), 'id': getblock(x, y, z)})
    return str(res)

def setblocks(*args):
    xs = []
    ys = []
    zs = []
    ds = []
    state = ''
    for a in args:
        if a == 'x' or a == 'y' or a == 'z' or a == 'id':
            state = a
        elif state == 'x':
            xs.append(int(a))
        elif state == 'y':
            ys.append(int(a))
        elif state == 'z':
            zs.append(int(a))
        elif state == 'id':
            ds.append(a)
    print(xs, ys, zs, ds)
    def sbs(xs_, ys_, zs_, ids_):
        for x, y, z, id in zip(xs_, ys_, zs_, ids_):
            b = world.getBlockAt(x, y, z)
            d = Material.matchMaterial(id).createBlockData()
            b.setBlockData(d)
    ps.scheduler.runTask(sbs, xs, ys, zs, ds)
    return None

def setblock(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z)
    d = Material.matchMaterial(args[3]).createBlockData()
    # wacky little workaround for sync block set
    def sb(block, data):
        block.setBlockData(data)
    ps.scheduler.runTask(sb, b, d)
    return None

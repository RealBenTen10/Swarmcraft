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

def getblock(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z).getBlockData().getAsString()
    return str(b)

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

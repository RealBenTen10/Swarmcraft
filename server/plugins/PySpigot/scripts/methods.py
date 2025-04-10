"""
Define server methods here
These will all be called asynchronously to the main server thread, so you can take your time here
Return values will be cast to a string and sent back to the client
If you do need to run things in a new (or sync) thread, use the pyspigot scheduler
"""

import pyspigot as ps
from org.bukkit import Bukkit, Location, Material
from org.bukkit.inventory import ItemStack

world = Bukkit.getWorld('world')
server = Bukkit.getServer()

def ping(*args):
    return 'pong'

# get the id of one block
def getblock(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z).getBlockData().getAsString()
    return str(b)

# get ids of many blocks
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

# set many blocks
# setblocks x 10 10 10 y 2 4 5 z -3 4 4 id dirt diamond_block gold
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
    def sbs(xs_, ys_, zs_, ids_):
        for x, y, z, id in zip(xs_, ys_, zs_, ids_):
            b = world.getBlockAt(x, y, z)
            d = Material.matchMaterial(id).createBlockData()
            b.setBlockData(d)
    ps.scheduler.runTask(sbs, xs, ys, zs, ds)
    return None

# set one block
# setblock 10 4 10 diamond_block
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

# for running commands on the server
# command tp player 0 0 0
def command(*args):
    def disp(cmd):
        server.dispatchCommand(server.getConsoleSender(), cmd)
    ps.scheduler.runTask(disp, ' '.join(args))
    return None

# get the contents of a chest at a given point
# if the chest is a double chest, only gets items in the part of the chest on the given block
# returns none if empty or not a chest
def getchest(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z)
    if b.getType() != Material.CHEST:
        return None
    ps.gv.remove('chest_inv')
    def ginv():
        ps.gv.remove('chest_inv')
        it = b.getState().getBlockInventory().iterator()
        # build dict of block types and item counts
        inv = {}
        while it.hasNext():
            stack = it.next()
            if stack is not None:
                if stack.getType() in inv:
                    inv[stack.getType()] += stack.getAmount()
                else:
                    inv[stack.getType()] = stack.getAmount()
        ps.gv.set('chest_inv', inv)
    ps.scheduler.runTask(ginv)
    while not ps.gv.contains('chest_inv'):
        pass
    inv = ps.gv.get('chest_inv')
    ps.gv.remove('chest_state')
    return str(inv)

# set the contents of a chest at a given point
# if the chest is a double chest, only sets items in the part of the chest on the given block
# returns none always, does nothing if given block not a chest
# setchest x y z id <item1> <item2> count <count1> <count2>
def setchest(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z)
    if b.getType() != Material.CHEST:
        return None
    ids = []
    counts = []
    state = ''
    for a in args[3:]:
        if a == 'id' or a == 'count':
            state = a
        elif state == 'id':
            ids.append(a)
        elif state == 'count':
            counts.append(int(a))
    def sinv():
        inv = b.getState().getBlockInventory()
        inv.clear()
        for id, count in zip(ids, counts):
            stack = ItemStack(Material.matchMaterial(id), count)
            inv.addItem(stack)
    ps.scheduler.runTask(sinv)
    return None

def clearchest(*args):
    x = int(args[0])
    y = int(args[1])
    z = int(args[2])
    b = world.getBlockAt(x, y, z)
    if b.getType() != Material.CHEST:
        return None
    def clearch():
        inv = b.getState().getBlockInventory()
        inv.clear()
    ps.scheduler.runTask(clearch)
    return None

# get the inventory of a given player
# returns none if empty or not a player
def getinventory(*args):
    p = Bukkit.getPlayer(args[0])
    if p is None:
        return None
    ps.gv.remove('player_inv')
    def ginv():
        ps.gv.remove('player_inv')
        it = p.getInventory().iterator()
        inv = {}
        while it.hasNext():
            stack = it.next()
            if stack is not None:
                if stack.getType() in inv:
                    inv[stack.getType()] += stack.getAmount()
                else:
                    inv[stack.getType()] = stack.getAmount()
        ps.gv.set('player_inv', inv)
    ps.scheduler.runTask(ginv)
    while not ps.gv.contains('player_inv'):
        pass
    inv = ps.gv.get('player_inv')
    ps.gv.remove('player_inv')
    return str(inv)

# set the inventory of a given player
# always returns none
# setinventory <player> id <item1> <item2> count <count1> <count2>
def setinventory(*args):
    p = Bukkit.getPlayer(args[0])
    if p is None:
        return None
    ids = []
    counts = []
    state = ''
    for a in args[1:]:
        if a == 'id' or a == 'count':
            state = a
        elif state == 'id':
            ids.append(a)
        elif state == 'count':
            counts.append(int(a))
    def sinv():
        inv = p.getInventory()
        inv.clear()
        for id, count in zip(ids, counts):
            stack = ItemStack(Material.matchMaterial(id), count)
            inv.addItem(stack)
    ps.scheduler.runTask(sinv)
    return None

def clearinventory(*args):
    p = Bukkit.getPlayer(args[0])
    if p is None:
        return None
    def clearinv():
        inv = p.getInventory()
        inv.clear()
    ps.scheduler.runTask(clearinv)
    return None
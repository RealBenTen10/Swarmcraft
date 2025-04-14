"""
Block and inventory change callbacks for logging purposes
"""
import time

import pyspigot as ps
from org.bukkit.event.block import BlockPlaceEvent, BlockDropItemEvent
from org.bukkit.event.inventory import InventoryCloseEvent
from org.bukkit.event.inventory.InventoryType import CHEST
import os.path

# block place is org.bukkit.event.block.BlockPlaceEvent
# block break event is org.bukkit.event.block.BlockDropItemEvent
def block_change(event):
    block = event.getBlock()
    x = block.getX()
    y = block.getY()
    z = block.getZ()
    mat = block.getType()
    block_logfile.write(str(time.time()) + ',' + str((x, y, z)) + ',' + str(mat) + '\n')

# player changing an inventory is org.bukkit.event.inventory.InventoryCloseEvent
# should check if the closed inventory is a chest
def inventory_close(event):
    inv = event.getInventory()
    if inv.getType() is not CHEST:
        return
    holder_pos_x = inv.getHolder().getX()
    holder_pos_y = inv.getHolder().getY()
    holder_pos_z = inv.getHolder().getZ()
    contents = inv.getContents() # array of stacks
    contents_dict = {}
    for stack in contents:
        if stack is not None:
            name = str(stack.getType())
            count = int(stack.getAmount())
            if name not in contents_dict:
                contents_dict[name] = count
            else:
                contents_dict[name] += count
    chests_logfile.write(str(time.time()) + ',' + str((holder_pos_x, holder_pos_y, holder_pos_z)) + ',' + str(contents_dict) + '\n')

bpl = ps.listener.registerListener(block_change, BlockPlaceEvent)
bbl = ps.listener.registerListener(block_change, BlockDropItemEvent)
icl = ps.listener.registerListener(inventory_close, InventoryCloseEvent)

log_dir = os.path.abspath(os.path.join(os.path.curdir, 'swarmcraft-log'))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

block_logfile_path = os.path.join(log_dir, 'blocks.log')
block_logfile = open(block_logfile_path, 'w')
block_logfile.write('start time ' + str(time.time()) + '\n')
block_logfile.write('time,position,block\n')

chests_logfile_path = os.path.join(log_dir, 'chests.log')
chests_logfile = open(chests_logfile_path, 'w')
chests_logfile.write('start time ' + str(time.time()) + '\n')
chests_logfile.write('time,position,contents\n')

print('Serverside swarmcraft logging to ' + str(log_dir))

def stop():
    block_logfile.close()
    chests_logfile.close()

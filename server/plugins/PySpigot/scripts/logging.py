"""
Block and inventory change callbacks for logging purposes
"""

import pyspigot as ps
from org.bukkit.event.block import BlockPlaceEvent, BlockDropItemEvent
from org.bukkit.event.inventory import InventoryCloseEvent
from org.bukkit.event.inventory.InventoryType import CHEST

# block place is org.bukkit.event.block.BlockPlaceEvent
def block_place(event):
    block = event.getBlock()
    x = block.getX()
    y = block.getY()
    z = block.getZ()
    mat = block.getType()
    print('Block placed: ' + str(mat) + ' at ' + str((x, y, z)))

# block break event is org.bukkit.event.block.BlockDropItemEvent
def block_break(event):
    block = event.getBlock()
    x = block.getX()
    y = block.getY()
    z = block.getZ()
    mat = block.getType() # this is the block type after breaking, not really that useful
    print('Block broken: ' + str(mat) + ' at ' + str((x, y, z)))

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
    print('chest at ' + str((holder_pos_x, holder_pos_y, holder_pos_z)) + ' contains:')
    for stack in contents:
        if stack is not None:
            print('\t' + str(stack.getType()) + 'x' + str(stack.getAmount()) + ' ')

bpl = ps.listener.registerListener(block_place, BlockPlaceEvent)
bbl = ps.listener.registerListener(block_break, BlockDropItemEvent)
icl = ps.listener.registerListener(inventory_close, InventoryCloseEvent)

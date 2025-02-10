'''
start server and control simulation here
'''
from time import sleep

from agent import Goto
from world_interface.pooler import pooler

for i in range(0, 20):
    pooler.create_agent(f'bot{i}', Goto)

while True:
    pooler.update_all_agents()

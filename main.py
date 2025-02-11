'''
start server and control simulation here
'''
import asyncio

from agent import Goto
from server import server
from world_interface.pooler import pooler

'''for i in range(0, 20):
    pooler.create_agent(f'bot{i}', Goto)

while True:
    pooler.update_active_agents()'''

def main():
    p = asyncio.run(server.start())
    for i in range(0, 20):
        a = pooler.create_agent(f'bot{i}', Goto)
    for i in range(0, 10):
        pooler.activate_agent()
    input("press enter to quit")
    server.stop()

if __name__ == '__main__':
    main()

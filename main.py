'''
start server and control simulation here
'''
import operator

from mazelib import Maze
from mazelib.generate.Wilsons import Wilsons
from test_evocraft_py import BRICK_BLOCK, AIR, DIAMOND_BLOCK, GOLD_BLOCK, GRASS

from agents.agent import Goto
from server import server
from world_interface.pooler import pooler, WORLD_CENTER
import javascript.connection

def main():
    server.start()
    print("Adding agents")
    for i in range(0, 10):
        a = pooler.create_agent(Goto)
    for i in range(0, 10):
        pooler.activate_agent()
    server.send_command('say Ready')
    print("Agents added")
    print("Ready")
    print("h for help, q to quit")
    while True:
        ipt = input("> ").split()
        if ipt[0] == "quit" or ipt[0] == "q":
            break
        elif ipt[0] == "help" or ipt[0] == "h":
            print("h for help, q to quit, r or reset to reset agents, anything else is sent to server")
        elif ipt[0] == "reset" or ipt[0] == "r":
            # reset and deactivate every agent
            # have to do it this way because we remove from list as we iterate
            while len(pooler.get_active_agents()) != 0:
                pooler.reset_agent(pooler.get_active_agents()[0])
                pooler.deactivate_agent(pooler.get_active_agents()[0])
        elif ipt[0] == "a" or ipt[0] == "activate":
            # activate an agent
            act = pooler.activate_agent()
            if act is not None:
                print("Activated " + str(act.id))
        elif ipt[0] == "run" or ipt[0] == "r" or ipt[0] == "start" or ipt[0] == "s":
            # run the loaded experiment
            pass
        elif ipt[0] == "evo-test":
            # test method for evocraft
            # generate a random maze
            # start is gold block, end is diamond block
            m = Maze()
            w = int(ipt[1])
            h = int(ipt[2])
            m.generator = Wilsons(w, h)
            m.generate()
            m.generate_entrances()
            print(m)
            server.fill_cube(WORLD_CENTER, tuple(map(operator.add, WORLD_CENTER, (1000, 5, 1000))), AIR)
            server.fill_cube(tuple(map(operator.add, WORLD_CENTER, (0, -1, 0))), tuple(map(operator.add, WORLD_CENTER, (1000, -1, 1000))), GRASS)
            blocks = []
            positions = []
            for x in range(len(m.grid)):
                for y in range(len(m.grid[x])):
                    if m.grid[x][y] == 1:
                        blocks.append(BRICK_BLOCK)
                        blocks.append(BRICK_BLOCK)
                    else:
                        blocks.append(AIR)
                        blocks.append(AIR)
                    positions.append((x + 10, 4, y + 10))
                    positions.append((x + 10, 5, y + 10))
                    blocks.append(BRICK_BLOCK)
                    positions.append((x + 10, 3, y + 10))
            blocks.append(DIAMOND_BLOCK)
            blocks.append(AIR)
            blocks.append(AIR)
            positions.append((m.start[0] + 10, 3, m.start[1] + 10))
            positions.append((m.start[0] + 10, 4, m.start[1] + 10))
            positions.append((m.start[0] + 10, 5, m.start[1] + 10))
            blocks.append(GOLD_BLOCK)
            blocks.append(AIR)
            blocks.append(AIR)
            positions.append((m.end[0] + 10, 3, m.end[1] + 10))
            positions.append((m.end[0] + 10, 4, m.end[1] + 10))
            positions.append((m.end[0] + 10, 5, m.end[1] + 10))
            server.spawn_blocks(positions, blocks)
        else:
            server.send_command(ipt)
    pooler.disconnect_all_agents() # stop the pooler (disconnect all the bots gracefully)
    server.stop() # stop the server
    javascript.connection.stop() # close the js bridge (prevents broken pipes)
    print("Server is DOWN!")
    exit()

if __name__ == '__main__':
    main()

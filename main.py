'''
start server and control simulation here
'''
import operator

from mazelib import Maze
from mazelib.generate.Wilsons import Wilsons
from test_evocraft_py import BRICK_BLOCK, AIR, DIAMOND_BLOCK, GOLD_BLOCK, GRASS

from agents.agent import Goto
from environments.environment import MazeEnv
from environments.forage_env import ForageEnvironment
from server import server
from util import add_tuples
from world_interface.pooler import pooler, WORLD_CENTER
import javascript.connection

def main():
    server.start()
    print("Adding agents")
    for i in range(0, 10):
        a = pooler.create_agent(Goto)
    server.send_command('say Ready')
    print("Agents added")
    print("Ready")
    print("h for help, q to quit")
    while True:
        ipt = input("> ").split()
        try:
            if ipt[0] == "quit" or ipt[0] == "q":
                break
            elif ipt[0] == "help" or ipt[0] == "h":
                print("h for help, q to quit, r or reset to reset agents, cmd <...> to send input to server")
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
                f = ForageEnvironment((10, 4, 10), (int(ipt[1]), 50, int(ipt[2])), 5, 10, int(ipt[3]))
                f.reset()
                f.initialize()
                #m = MazeEnv((10, 4, 10), (int(ipt[1]), 50, int(ipt[2])))
                #m.reset()
                #m.initialize()
            elif ipt[0] == "clear":
                server.fill_cube(WORLD_CENTER, add_tuples(WORLD_CENTER, (int(ipt[1]), int(ipt[2]), int(ipt[3]))), AIR)
            elif ipt[0] == "cmd":
                server.send_command(" ".join(ipt[1:]))
            else:
                print("Unknown command")
        except Exception as e:
            print(e)
    pooler.disconnect_all_agents() # stop the pooler (disconnect all the bots gracefully)
    server.stop() # stop the server
    javascript.connection.stop() # close the js bridge (prevents broken pipes)
    print("Server is DOWN!")
    exit()

if __name__ == '__main__':
    main()

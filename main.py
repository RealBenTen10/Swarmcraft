'''
start server and control simulation here
'''
from agents.agent import Goto
from server import server
from world_interface.pooler import pooler
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
        ipt = input("> ")
        if ipt == "quit" or ipt == "q":
            break
        elif ipt == "help" or ipt == "h":
            print("h for help, q to quit, r or reset to reset agents, anything else is sent to server")
        elif ipt == "reset" or ipt == "r":
            # reset and deactivate every agent
            # have to do it this way because we remove from list as we iterate
            while len(pooler.get_active_agents()) != 0:
                pooler.reset_agent(pooler.get_active_agents()[0])
                pooler.deactivate_agent(pooler.get_active_agents()[0])
        elif ipt == "a" or ipt == "activate":
            # activate an agent
            act = pooler.activate_agent()
            if act is not None:
                print("Activated " + str(act.id))
        elif ipt == "run" or ipt == "r" or ipt == "start" or ipt == "s":
            # run the loaded experiment
            pass
        elif ipt == "evo-test":
            # test method for evocraft
            pass
        else:
            server.send_command(ipt)
    pooler.disconnect_all_agents() # stop the pooler (disconnect all the bots gracefully)
    server.stop() # stop the server
    javascript.connection.stop() # close the js bridge (prevents broken pipes)
    print("Server is DOWN!")
    exit()

if __name__ == '__main__':
    main()

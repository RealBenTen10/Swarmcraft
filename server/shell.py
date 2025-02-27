import cmd
from typing import Any

import javascript.connection
from test_evocraft_py import AIR

from agents.agent import Agent
from environments.environment import MazeEnv
from environments.forage_env import ForageEnvironment
from util import add_tuples
from world_interface.pooler import pooler, WORLD_CENTER
from server.server import server


class ServerShell(cmd.Cmd):
    intro = "Shell for swarmcraft simulator. Type help or ? to list commands.\n"
    prompt = "swarmcraft > "
    file = None

    def cmdloop(self, intro: Any | None = None):
        try:
            super().cmdloop(intro)
        except Exception as e:
            print(e)
            #self.do_quit([])

    def do_lsagents(self, args):
        """List all active and pooled agents"""
        print("Active agents:")
        for a in pooler.active_agents:
            print("\t" + str(a))
        print("Pooled agents:")
        for a in pooler.agents_pool:
            print("\t" + str(a))

    def do_addagent(self, args):
        """Add one or n new agents"""
        at = args.split()
        if at:
            for i in range(int(at[0])):
                pooler.create_agent(Agent) # TODO: user-configurable agent constructors
        else:
            pooler.create_agent(Agent)

    def do_activateagent(self, args):
        """Activate one or n pooled agents"""
        at = args.split()
        if at:
            for i in range(int(at[0])):
                act = pooler.activate_agent()
                if act is not None:
                    print("Activated " + str(act))
        else:
            act = pooler.activate_agent()
            if act is not None:
                print("Activated " + str(act))

    # TODO: user-selectable resets
    def do_resetagents(self, args):
        """Reset and deactivate every agent"""
        while len(pooler.active_agents) > 0:
            pooler.reset_agent(pooler.active_agents[0])
            pooler.deactivate_agent(pooler.active_agents[0])

    # TODO: user-selectable experiments
    def do_run(self, args):
        """Run an experiment"""
        at = args.split()
        f = ForageEnvironment((10, 4, 10), (int(at[0]), 50, int(at[1])), 5, 10, int(at[2]))
        f.reset()
        f.initialize()

    def do_mazegen(self, args):
        """Generate an nxn maze"""
        at = args.split()
        m = MazeEnv((10, 4, 10), (int(at[0]), 10, int(at[1])))
        m.reset()
        m.initialize()

    def do_clear(self, args):
        """Clear an area"""
        at = args.split()
        server.fill_cube(WORLD_CENTER, add_tuples(WORLD_CENTER, (int(at[0]), int(at[1]), int(at[2]))), AIR)

    def do_cmd(self, args):
        """Send a command to the server"""
        server.send_command(args)

    def do_quit(self, args):
        """Stop the server and exit this shell"""
        print("Server going down...")
        """Stop the server and exit"""
        for a in pooler.active_agents:
            a.bot.quit()
        for a in pooler.agents_pool:
            a.bot.quit()
        server.stop()
        javascript.connection.stop()
        print("Server is DOWN!")
        return True

import cmd
from typing import Any

import javascript.connection
from test_evocraft_py import AIR

from environments.environment import MazeEnv
from experiments.experiment import ExampleExperiment
from experiments.forage_exp import ForageExperiment
from util import add_tuples
from server.pooler import pooler, WORLD_CENTER
from server.minecraft_server import minecraft_server


class ServerShell(cmd.Cmd):
    intro = "Shell for swarmcraft simulator. Type help or ? to list commands.\n"
    prompt = "swarmcraft > "
    file = None

    def cmdloop(self, intro: Any | None = None):
        try:
            super().cmdloop(intro)
        except Exception as e:
            print(e)
            #super().cmdloop('')
            self.do_quit([])

    def do_lsbots(self, args):
        """List all bound and free bots"""
        print(f'Bound bots ({len(pooler.bound_bots)}):')
        for b in pooler.bound_bots:
            print("\t" + b.username)
        print(f'Free bots ({len(pooler.free_bots)}):')
        for b in pooler.free_bots:
            print("\t" + b.username)

    def do_addbot(self, args):
        """Add a new free bot"""
        at = args.split()
        if at:
            for i in range(int(at[0])):
                pooler.create_bot()
        else:
            pooler.create_bot()

    def do_resetbots(self, args):
        """Reset all free bots"""
        for b in pooler.free_bots:
            pooler.reset_bot_stats(b)
            pooler.reset_bot_position(b)

    def do_prunebots(self, args):
        """Remove all free bots"""
        while len(pooler.free_bots) > 0:
            b = pooler.free_bots.pop()
            b.quit()

    # TODO: user-selectable experiments
    def do_run(self, args):
        """Run an experiment"""
        at = args.split()
        """f = ForageEnvironment((10, 4, 10), (int(at[0]), 50, int(at[1])), 5, 10, int(at[2]))
        f.reset()
        f.initialize()"""
        ex = ForageExperiment(int(at[0]))
        ex.initialize()
        ex.run()
        ex.cleanup()

    def do_mazegen(self, args):
        """Generate an nxn maze"""
        at = args.split()
        m = MazeEnv((10, 4, 10), (int(at[0]), 10, int(at[1])))
        m.reset()
        m.initialize()

    def do_clear(self, args):
        """Clear an area"""
        at = args.split()
        minecraft_server.fill_cube(WORLD_CENTER, add_tuples(WORLD_CENTER, (int(at[0]), int(at[1]), int(at[2]))), AIR)

    def do_cmd(self, args):
        """Send a command to the server"""
        print(minecraft_server.send_command(args))

    def do_quit(self, args):
        """Stop the server and exit this shell"""
        print("Server going down...")
        """Stop the server and exit"""
        for b in pooler.bound_bots:
            b.quit()
        for b in pooler.free_bots:
            b.quit()
        minecraft_server.stop()
        javascript.connection.stop()
        print("Server is DOWN!")
        return True

    def do_readcube(self, args):
        """Read a cube and print the results to console"""
        at = args.split()
        blocks = minecraft_server.read_cube((int(at[0]), int(at[1]), int(at[2])), (int(at[3]), int(at[4]), int(at[5])))
        print(blocks)

    def do_readblock(self, args):
        """Read a block and print the results to console"""
        at = args.split()
        block = minecraft_server.read_block((int(at[0]), int(at[1]), int(at[2])))
        print(block)

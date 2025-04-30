import os

from swarmcraft.messaging import MessageServer
from swarmcraft.minecraft.server import MinecraftServer
from swarmcraft.pooler import Pooler
from swarmcraft.shell import ServerShell

USER_AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'agents'))
USER_BEHAVIORS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'behaviors'))
USER_ENVS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'environments'))
USER_EXPS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'experiments'))

def main():
    # minecraft server
    server = MinecraftServer()
    ok = server.start()
    if not ok:
        exit(1)

    # once the server's up, we can add the pooler and the messenger
    pooler = Pooler(server)
    messenger = MessageServer()

    # start the shell
    server.send("command say Ready")
    print("User agents directory:", USER_AGENTS_DIR)
    print("User behaviors directory:", USER_BEHAVIORS_DIR)
    print("User environments directory:", USER_ENVS_DIR)
    print("User experiments directory:", USER_EXPS_DIR)
    ServerShell(server, pooler, messenger).cmdloop()

if __name__ == '__main__':
    main()

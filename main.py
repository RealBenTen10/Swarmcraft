from server.minecraft_server import minecraft_server
from server.pooler import pooler
from server.shell import ServerShell

def main():
    # start the server
    minecraft_server.start()

    # create and initialize the initial bot pool
    for _ in range(10):
        pooler.create_bot()
    for b in pooler.free_bots:
        pooler.reset_bot_stats(b)
        pooler.reset_bot_position(b)

    minecraft_server.send_command('say Ready')
    print("Ready")
    ServerShell().cmdloop()

if __name__ == '__main__':
    main()

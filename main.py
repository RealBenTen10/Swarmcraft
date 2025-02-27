from server.server import server
from server.shell import ServerShell

def main():
    server.start()
    server.send_command('say Ready')
    print("Ready")
    ServerShell().cmdloop()

if __name__ == '__main__':
    main()

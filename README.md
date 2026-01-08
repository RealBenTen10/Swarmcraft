@max
Still using the docs branch :)

# Swarmcraft
This is a framework for minecraft-based multi-agent simulations.
Users can create behavior-tree powered agents and run experiments in custom environments.
Logging tools are also included.

## Requirements
- Python 3.8 or newer
- pip
- NodeJS
- npm
- Java 8
- Minecraft 1.21.1

## Installation
Clone the repository:
```
$ git clone git@gitlab.inf.uni-konstanz.de:max.oltmanns/swarmcraft.git
$ cd swarmcraft
```
Install python libraries:
```
.../swarmcraft $ pip install -r requirements.txt
```
Install mineflayer:
```
.../swarmcraft $ npm install mineflayer
```

### Installation troubleshooting
- on some systems, installing Node via npm causes issues with the python-javascript bridge (errors like `failed to start bridge!` on launching the simulator). Fixed by installing Node through the system package manager.

## Use
### Structure
Swarmcraft is structured as follows:
```
swarmcraft
├── agents
├── behaviors
├── environments
├── experiments
└── swarmcraft
```
The folders `agents`, `behaviors`, `environments` and `experiments` are where user-defined agents, agent behaviors, environments and experiments should be placed, respectively.
These folders are pre-populated with an example foraging experiment, and each folder contains a further README about its functionality.

`swarmcraft` contains the simulator internals.

### Conceptual overview
In Swarmcraft, users run **experiments** which consist of **environments** and **agents**.
These objects are defined as python scripts in their respective folders (see *Structure*) and loaded/executed at runtime from a shell.

Internally, these actions are orchestrated by several systems, the most important of which are the **pooler**, the **minecraft server**, and the **message server**.

#### Pooler
Because initializing new players is expensive, it is in the interest of performance to reuse players where possible and swap out their controllers instead of disconnecting and reconnecting every time.
To achieve this, Swarmcraft distinguishes between **players/bots**, which are the actual in-game avatars, and **agents**, which are scripts that can be assigned to control players.
The pooler (`swarmcraft/pooler.py`) implements this functionality by maintaining a collection of unused bots and binding these to agents upon request.

#### Minecraft server
Swarmcraft exposes parts of the minecraft server in order to perform actions such as executing minecraft commands or setting/reading blocks.
This is implemented as a socket connection to a [PySpigot](https://github.com/magicmq/pyspigot) script which parses and executes commands (henceforth referred to as the **minecraft endpoint**).
Available commands can be seen at `swarmcraft/minecraft/plugins/PySpigot/scripts/methods.py`.
For a usage example, see `environments/forage.py`.
The minecraft endpoint can also be accessed directly from the swarmcraft shell.

#### Message server
This simulator was designed with swarm robotics in mind, so it was deemed necessary to implement a system by which agents could communicate with each other.
Although agents are capable of reading from and writing to the minecraft server's chat, sending too many messages at once causes the server's rate limiter to kick the offending player.
Because of this, Swarmcraft provides its own messaging capabilities in `swarmcraft/messaging.py`.
After being registered on the message server, agents can send messages globally, locally, or secretly.

### Launching
`swarmcraft/swarmcraft` contains the simulator internals, as well as the launch point `main.py`.
Running `main.py` will start the minecraft server and swarmcraft shell.
Once the server has started, users can connect and watch on the host system by launching minecraft and connecting to the multiplayer server at `127.0.0.1`.

## Acknowledgements
- [PySpigot](https://github.com/magicmq/pyspigot)
- [Mineflayer](https://github.com/PrismarineJS/mineflayer/tree/master)

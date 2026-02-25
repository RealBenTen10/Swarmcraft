# Swarmcraft
This is a framework for minecraft-based multi-agent simulations.
Users can create agents and run experiments in custom environments.
Logging tools are also included, as well as a suite of tools for behavior-tree-based agent control.

# Installation/Setup
Cloning the repository is already half the battle. In case you haven't done so yet:
- `git clone https://gitlab.inf.uni-konstanz.de/max.oltmanns/swarmcraft.git`

## Requirements
For the rest of the installation process, the following tools are required:
- `jdk` (>= 21)
- `python` (>= 3.12)
- `nodejs` (>= 22)
- `npm` (11.3.0)
- Minecraft launcher (e.g. https://atlauncher.com/downloads) with Minecraft 1.21.1

## Installing the minecraft server
Once the clone is complete, move to the server install tools directory:
- `cd swarmcraft/swarmcraft/server_install`

Run the installation script `install.sh`. The script requires confirmation at several steps.
- `./install.sh`

This will download and run the Spigot buildtools and create a jarfile for a minecraft server version 1.21.1.
Additionally, the `pyspigot` plugin (ver. 0.8.0) is installed and configured.
The minecraft server and its plugins are installed at `swarmcraft/swarmcraft/minecraft`.

## Installing python and node libraries
Several additional libraries are required. Navigate to the workspace directory (the root of the repository, which contains the directories `agents`, `behaviors`, `environments`, `experiments`, `swarmcraft`) and install the necessary packages.

Install node packages:
- `npm install mineflayer`

A python virtual environment is recommended:
- `python3 -m venv .venv`
- `source .venv/bin/activate`

Install python packages:
- `pip install -r requirements.txt`

## Viewing clients
Swarmcraft does not provide an interface to view running experiments other than the swarmcraft and server consoles.
In order to log into the server as a player and observe running experiments, you will need a copy of Minecraft, available at https://www.minecraft.net/en-us/download.

## Troubleshooting
- on some systems, installing Node via npm causes issues with the python-javascript bridge (errors like `failed to start bridge!` on launching the simulator). Fixed by installing Node through the system package manager.

# Using swarmcraft

## Repository structure
The repository root, or *workspace*, is named `swarmcraft` and includes the directories `agents`, `behaviors`, `environments`, `experiments`, and `swarmcraft`.
When swarmcraft is run for the first time, a logging directory is also generated under `logs`.

The directory at `swarmcraft/swarmcraft` is referred to as the *installation directory*.
It contains:
- the swarmcraft source code
- the minecraft server executable and plugins (`swarmcraft/swarmcraft/minecraft`) (referred to as the *minecraft installation directory*)
- the minecraft server installation utilities (`swarmcraft/swarmcraft/server_install`) (referred to as the *minecraft installation utilities*)
- the behavior tree toolkit python module (`swarmcraft/swarmcraft/btree`) (referred to as the *behavior tree toolkit* or *btree toolkit*)
- swarmcraft's documentation (`swarmcraft/swarmcraft/docs`)

## Launching swarmcraft
After installing swarmcraft, the minecraft server and swarmcraft shell can be started from the workspace:
- activate the virtual environment (`source .venv/bin/activate`)
- launch swarmcraft (`python3 swarmcraft/main.py`)

After a short wait, the server console window and swarmcraft shell should both become available.
This can take up to a few minutes on slow systems.
If swarmcraft hangs during startup, it may be because another instance of a minecraft server is already running, or was not properly shut down because swarmcraft crashed or exited incorrectly during its last run.
To resolve this, simply kill the java server process with your system's process manager and rerun swarmcraft.

### Further server configuration
Configuration of the minecraft server may be necessary.
The server configuration file `server.properties` is located in the minecraft installation directory.

## Experiments
Experiments are routines which can be launched from the swarmcraft shell.
They consist of startup, update, and cleanup methods.
Experiments can also accept arguments from the shell such as the number of agents to use during a run.
Currently, swarmcraft does not support a method for cancelling running experiments short of killing the swarmcraft process.
For more information regarding experiments, the agents that take part in them, and the environments they take place in, see the accompanying documentation in `swarmcraft/docs/agents.md`, `swarmcraft/docs/environments.md`, and `swarmcraft/docs/experiments.md`.
The API used to send commands to the Minecraft server is documented in `swarmcraft/docs/mc-api.md`.

## Behavior tree toolkit
Swarmcraft was written with behavior tree-based control in mind.
To this end, a small behavior tree library is provided under `swarmcraft/swarmcraft/btree`.
The library includes a selection of nodes which interface with swarmcraft agents as well as algorithms for genetic evolution.
See `swarmcraft/swarmcraft/btree/README.md` for further documentation.
A behavior tree folder is also provided in the workspace under `swarmcraft/behaviors`, although users are free to put their behavior tree definitions wherever they want.

# Acknowledgements
- [PySpigot](https://github.com/magicmq/pyspigot)
- [Mineflayer](https://github.com/PrismarineJS/mineflayer/tree/master)

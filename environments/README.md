# Environments

Classes that override `Envrionment` describe how to set up and tear down environments for experiments.
They can also be used to generate logging snapshots.
Like experiments, environments can be hotloaded.
To do so, save your changes and run `reloadenvs` in the shell.

The base class, in `swarmcraft/environment.py`, provides four template methods:
- `\_\_init__(minecraft_server, origin, size)`: the default constructor associates the environment with the passed minecraft server and sets the environment's origin point as well as its size. The origin is in the environment's corner, not its center. The transformation from environment space to world space is `world_space = origin + env_space`.
- `reset()`: Cleanup method used by `Experiment`. By default, sets all blocks in the environment to air.
- `initialize()`: Setup method used by `Experiment`. By default, builds a ground plane of grass blocks and a fence around the edge of the environment.
- `log()`: Logging method. Should return a one-row DataFrame. By default, returns an empty DataFrame.

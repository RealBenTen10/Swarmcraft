# Experiments

Experiments define a setup routine, an update loop, and a teardown routine.
They are designed to be hot-loadable, in that several different experiments can be run without needing to exit and restart Swarmcraft.
Experiments can also be edited without needing to restart by saving the experiment and running `reloadexps` in the shell.
Experiments manage environments and agents, as well as the logging thereof.

Experiments can be launched from the Swarmcraft shell with `run <Experiment> <args>`. 
`<Experiment>` must be the exact name of an `Experiment` subclass located in a file in `experiments`.
Any arguments passed after the experiment name will be passed to the experiment's constructor, along with:
- a `Pooler` (at `self.pooler`)
- a `MinecraftServer` (at `self.minecraft_server`)
- a `MessageServer` (at `self.message_server`)

The constructor should be overridden, as this is where an environment is defined and agents can be requested from the pooler.
The environment should be set at `self.environment`.
Agents should be appended to the list at `self.agents`.

When they are launched, experiments are automatically assigned a log directory in `logs/<experiment name>-<launch time>`.
This directory is accessible as a `pathlib` `Path` object under `self.log_dir`, and is where agent and environment logs are saved.

After the log directory is set, the shell calls, in sequence:
- `initialize()`: By default, this resets and initializes the experiment's environment, and resets any agents assigned to the experiment.
- `run()`: By default, does nothing. This is where the actual experiment should take place: an update loop, any kind of logging, etc.
- `cleanup()`: By default, calls `destroy()` on all agents assigned to this experiment and calls `reset()` on the environment.

Experiments are blocking while they run.
Once the experiment is over, or an error is raised, control is returned to the shell.

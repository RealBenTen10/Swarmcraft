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


# README – Swarm-Compatible Genetic Programming Framework

## 1. System Overview

This project implements a complete experimental framework for evolving swarm-based agent behaviors using genetic programming (GP). The system integrates four tightly coupled subsystems:

1. A **shell-based user interface** for interactive control
2. A **configuration resolution pipeline** for defining experiments
3. A **genetic programming engine** for evolving behavior trees
4. A **logging and checkpointing subsystem** for reproducibility

The core design principle is separation of concerns: configuration, evolution, and environment execution are modular, but interact through clearly defined interfaces.

---

## 2. Entry Point and Execution Flow

### 2.1 Starting the System

The user starts the system by executing:

python main.py

This launches an interactive shell. All interactions, including experiment execution, are performed through this shell.

### 2.2 Shell Command: `run`

The primary command is:

run [flags] [positional arguments]

Internally, this command invokes `do_run(self, args)`.

---

## 3. Run Execution Pipeline (`do_run`)

The function `do_run` orchestrates the complete lifecycle of an experiment.

### Step 1: Configuration Resolution

run_cfg = resolve_run_config(args)

This produces a fully specified configuration dictionary.

### Step 2: Directory Creation

run_meta = create_run_directories()

Creates a unique directory `./logging/run_N/` and subdirectory `populations/`.

### Step 3: Persist Configuration

The resolved configuration is written to:

experiment_setup.txt

### Step 4: Summary Output

print_run_config_summary(run_cfg)

Displays all relevant parameters.

### Step 5: Experiment Initialization

exp = self.experiments[exp_name](...)

The experiment receives environment parameters such as arena size, origin, and runtime settings.

### Step 6: Primitive Setup

reset_primitives()
generate_pset()

* `reset_primitives()` clears global primitive registries
* `generate_pset()` registers control and action primitives

### Step 7: Swarm Initialization

agents = exp.initialize(run_cfg["swarm_size"])

Agents are created once and reused across evaluations.

### Step 8: Evolution Execution

population = ea_mu_plus_lambda(...)

Runs the full GP loop.

---

## 4. Configuration System (Detailed)

### 4.1 Parsing Arguments

`parse_run_args(args)` extracts:

* `--preset`
* `--resume`
* `--resume-from`
* positional arguments

### 4.2 Resolution Pipeline (`resolve_run_config`)

The configuration is built in layers:

1. `default_run_config()`
2. `load_preset_config()`
3. resume logic (`load_previous_run_config_for_checkpoint`)
4. `apply_positional_overrides()`
5. `finalize_config()`

### 4.3 Finalization (`finalize_config`)

Key operations:

* Normalize vectors (`arena_origin`, `arena_size`)
* Compute:

lambda_ = population_count * offspring_multiplier

* Expand mission schedule into per-generation list
* Derive total generation count

---

## 5. Primitive System

### 5.1 Registries

* `CONTROL_PRIMITIVES`
* `ACTION_PRIMITIVES`
* `ACTION_PRIMITIVE_BY_CLS`

### 5.2 Control Primitives

Registered via:


register_control(cls, min_arity, max_arity)


Defines branching structure.

### 5.3 Action Primitives

Registered via:


register_action(cls, param_generators)


Each action can generate parameters dynamically.

---

## 6. Tree Generation

### 6.1 Grow Algorithm

`generate_grow_tree()` constructs trees recursively:

* Random height selected
* At each node:

  * stop → create action node
  * continue → create control node

### 6.2 Action Instantiation


_random_action()


* selects primitive
* samples parameters

---

## 7. Tree Utilities

### 7.1 Traversal

* `collect_nodes()` returns nodes with parent references

### 7.2 Mutation Points

* `collect_mutation_points()` includes:

  * nodes
  * parameter terminals

### 7.3 Metrics

* `tree_length()` counts nodes and parameters
* `tree_max_depth()` computes depth

---

## 8. Genetic Operators

### 8.1 Crossover

cx_one_point()


* randomly selects subtree in each parent
* swaps subtrees

### 8.2 Mutation


mut_grow()

Two modes:

1. Subtree replacement
2. Parameter mutation

---

## 9. Variation (`var_or`)

Implements probabilistic operator selection:

* crossover
* mutation
* reproduction

Each offspring is generated independently.

---

## 10. Selection

### 10.1 Tournament Selection


tournament_selection()


* sample subset
* choose best

### 10.2 Elitism


select_elites()


* preserve top individuals

---

## 11. Evolution Loop (`ea_mu_plus_lambda`)

### Initialization

* load checkpoint OR
* generate initial population

### Per Generation

1. Evaluate parents
2. Generate offspring
3. Evaluate offspring
4. Log results
5. Select elites
6. Select survivors
7. Save checkpoint

---

## 12. Fitness Evaluation

Defined in `evaluate_controller()`.

Steps:

* detect generation change
* shuffle environment
* assign controller
* run experiment multiple times
* average rewards
* apply complexity penalty

---

## 13. Logging System

### CSV Logging

`log_generation()` writes:

* generation
* tree string
* length
* depth
* fitness

### Checkpoints

* `save_population()`
* `load_population()`

Stores population and metadata.

---

## 14. Agent Binding

### Binding


bind_agent(tree, agent)


Assigns agent references to action nodes.

### Instantiation


instantiate_for_swarm()


Creates one tree per agent.

---

## 15. System Interaction Flow

1. User runs system
2. Shell command executed
3. Configuration resolved
4. Experiment created
5. Primitive set initialized
6. Population generated
7. Evolution loop runs
8. Logging and checkpointing performed

---

## 16. Reproducibility

Each run stores:

* full configuration
* full populations
* logs

This guarantees exact reproducibility.

---

## 17. Summary

The system provides a complete, modular implementation of swarm-based genetic programming. It integrates configuration management, evolutionary search, and experiment execution into a unified workflow, while maintaining reproducibility and extensibility at all stages.

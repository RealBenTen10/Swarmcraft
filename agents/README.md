# Agents

Agents are classes which can be bound to bots and used to control their interactions with the environment.
Upon binding, an agent is supplied with references to sensor (`agent.bot.sensing`) and controller (`agent.bot.actuation`) suites, as well as a reference to the message server.
The base class (`swarmcraft/agent.py`) defines several methods and a constructor which should be overridden for proper functionality:
- `__init__(pooler, message_server, uid)`: by default does nothing except binding the agent to a bot in the pooler. Can be overridden, a call to super().\_\_init__() should be present.
- `update()`: intended to be called by the experiment making use of this agent. Does nothing by default.
- `reset()`: intended to be called by the experiment making use of this agent during its cleanup routine. By default, asks the pooler to reset the bound bot's stats (inventory, health, etc) and teleport it back to the staging area. Should be overridden, with a call to super().reset()
- `log()`: intended to be called periodically by the experiment making use of this agent for logging purposes. By default, returns a one-row DataFrame containing the bot's internal ID and username.
- `destroy()`: intended to be called by the experiment making use of this agent when it is discarded/destroyed. Should __not__ be overridden unless you allocate objects in the agent which need further dynamic cleanup, in which case super().destroy() must be called for proper bot unbinding.

Agents do not execute in their own threads.
Therefore, it is not advised to write `update()` in such a way that it blocks execution for long.
Behavior trees lend themselves well to this design, and a basic behavior tree library is available at `swarmcraft.btree.nodes`.

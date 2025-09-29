# Agents (`swarmcraft/swarmcraft/agent.py`)
Agents are program-controlled minecraft player characters.
They can interact with their environment and send each other messages.

## The agent-bot abstraction
A distinction must be made between *agents* and *bots*.
Agents are python objects which must be bound to an available bot to interact with the minecraft world.
Upon binding, agents are supplied with references to sensor and actuator suites, as well as a reference to the swarmcraft-internal message server.
The *pooler* (`swarmcraft/swarmcraft/pooler.py`) manages binding and unbinding and keeps a list of free bots.
See `swarmcraft/experiments/example.py` for a working example.

## The base Agent class
### Fields
#### `self.bot`
Reference to the currently bound bot, `None` if the agent is unbound
#### `self.pooler`
Reference to the swarmcraft pooler
#### `self.message_server`
Reference to the internal message server. Prefer this over sending minecraft chats, as they are rate-limited and the message server is not.
#### `self.id`
Internal identifier used by logging functions and the message server. Should be unique.

### Methods
#### `__init__(self, pooler, message_server, uid)`
The base constructor accepts the pooler, the message server, and a unique identifier.
By default, the constructor also attempts to bind the agent to a free bot, and raises an exception if it cannot.
If you override this constructor, make sure to either call `super()` or bind a bot somewhere else.
If you write your own binding routine, it is recommended to take a look at the one provided in this constructor to make sure you don't miss anything.
#### `update(self)`
This is called once per update by the experiment this agent is a part of.
By default, does nothing.
#### `reset(self)`
Resets the agent to some initial state, but does not unbind the bot.
Used by experiment reset methods to wipe the slate clean.
By default, resets the agent's position to the pooling location, resets their statistics (health, hunger, effects, etc.), clears their inventory, and clears control states.
#### `log(self) -> dict`
Called by the experiment's logger to get a snapshot of agent state.
The logger does not index log entries in any way, so it is recommended to make sure that the dict returned is uniquely identifiable in some way.
By default, returns a dict with current time, agent id, and bot username fields.
#### `destroy(self)`
This method handles all cleanup associated with this agent.
It unbinds the agent's bot and returns it to the pooler's free bot pool, removes event listeners from the bot, deregisters the agent from the message server, and destroys the sensing and actuation suites.
It does not remove the agent from memory.
#### `__str__(self)`
Builtin string cast method for agents.
Returns a string of the output of `log(self)`.

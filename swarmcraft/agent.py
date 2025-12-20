import time

from swarmcraft.actuation import Actuation
from swarmcraft.messaging import MessageServer
from swarmcraft.pooler import Pooler
from swarmcraft.sensing import Sensing

# base agent class
class Agent(object):
    """Agents are program-controlled minecraft player characters.
    They can interact with their environment and send each other messages.
    """
    def __init__(self, pooler: Pooler, message_server: MessageServer, uid):
        """Default agent constructor binds to a free bot from the pooler, sets up actuation and sensing, and registers with message server.

        :param pooler: active pooler instance. Made available in experiments.
        :param message_server: active message server instance. Made available in experiments.
        :param uid: internal identifier for this agent, used by logging functions and the message server. Must be unique.
        """
        self.bot = None
        self.pooler = pooler
        self.message_server = message_server
        if pooler.bind_bot(self): # ask the pooler for a bot
            self.sensing = Sensing(self)
            self.actuation = Actuation(self)
            self.id = uid # internal id (use this for sending chats over the internal server, or tracking individual agents instead of bots)
            self.message_server.register(self) # register yourself with the message server
        else:
            raise Exception('Could not bind bot! (No free bots left)')

    def update(self):
        """Tick this agent's behavior trees, or perform other work."""
        pass

    def reset(self):
        """Reset this agent to an initial state.
        By default, resets agents to pooler origin, clears stats and inventory, and clears control states.
        """
        self.pooler.reset_bot_position(self.bot)
        self.pooler.reset_bot_stats(self.bot)
        self.actuation.stop()

    def log(self) -> dict:
        """Called periodically by the logger.
        Should return a dict, with at least one uniquely identifiable key (log entries are not indexed).
        """
        return {
            'time': time.time(),
            'id': str(self.id),
            'bot': 'None' if self.bot is None else self.bot.username,
        }

    def get_uid(self):
        return self.id

    def destroy(self):
        """Destroy this agent.
        Performs cleanup such as freeing the attached bot and deregistering from the message server.
        """
        try:
            self.bot.removeAllListeners()
            self.pooler.unbind_bot(self)
            self.message_server.deregister(self)
            self.sensing = None
            self.actuation = None
        except Exception as e:
            print(f"Error while destroying agent: {e}")
            pass

    def __str__(self):
        """String representation of this agent.
        By default, returns stringified output of self.log().
        """
        return str(self.log())

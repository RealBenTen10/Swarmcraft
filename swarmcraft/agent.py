from typing import override

from behaviors.Examples import GotoPoint
from swarmcraft.actuation import Actuation
from swarmcraft.messaging import MessageServer
from swarmcraft.pooler import Pooler
from swarmcraft.sensing import Sensing

# base agent class
class Agent(object):
    def __init__(self, pooler: Pooler, message_server: MessageServer, uid):
        self.bot = None
        self.pooler = pooler
        self.message_server = message_server
        if pooler.bind_bot(self): # ask the pooler for a bot
            self.sensing = Sensing(self)
            self.actuation = Actuation(self)
            self.id = uid # internal id (use this for sending chats over the internal server)
            self.message_server.register(self) # register yourself with the message server

    def update(self):
        """Tick this agent's behavior trees, or perform other work"""
        pass

    def reset(self):
        """Reset this agent to an initial state"""
        self.pooler.reset_bot_position(self.bot)
        self.pooler.reset_bot_stats(self.bot)
        pass

    def log(self):
        """Called periodically by the logger
        Should return a dict object"""
        return {
            'id': str(self.id),
            'bot': 'None' if self.bot is None else self.bot.username,
        }

    def destroy(self):
        """Destroy this agent
        Performs cleanup such as freeing the attached bot and deregistering from the message server"""
        self.pooler.unbind_bot(self)
        self.message_server.deregister(self)

    def __str__(self):
        return str(self.log())

class GotoAgent(Agent):
    def __init__(self, pooler, message_server, internalid):
        super().__init__(pooler, message_server, internalid)
        self.behavior = GotoPoint(self.sensing, self.actuation, (-169, 4, 1220))

    @override
    def update(self):
        status = self.behavior.tick()

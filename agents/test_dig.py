from swarmcraft.agent import Agent
from swarmcraft.util import add_tuples


class Digger(Agent):
    def __init__(self, pooler, message_server, uid):
        super().__init__(pooler, message_server, uid)
        self.dug = False

    def update(self):
        self.actuation.look_at(self.sensing.get_position())
        self.actuation.start_dig()
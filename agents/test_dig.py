from swarmcraft.agent import Agent
from swarmcraft.util import add_tuples


class Digger(Agent):
    def __init__(self, pooler, message_server, uid):
        super().__init__(pooler, message_server, uid)
        self.state = 'init'

    def update(self):
        if self.state == 'init':
            self.actuation.look_at((21, -59, 20))
            while not self.actuation.start_dig():
                pass
            self.state = 'digging'
        if self.state == 'digging':
            self.actuation.select_hotbar(0)
            if self.sensing.get_held_item() is not None:
                print('holding item')
                self.state = 'done digging'
        if self.state == 'done digging':
            self.state = 'building'
            self.actuation.place_block((0, 1, 0))
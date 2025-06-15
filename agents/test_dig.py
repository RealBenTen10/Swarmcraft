from swarmcraft.agent import Agent
from swarmcraft.btree.manipulation import CheckAllBlocksAtFeet


class Digger(Agent):
    def __init__(self, pooler, message_server, uid):
        super().__init__(pooler, message_server, uid)
        self.state = 'init'
        self.test = CheckAllBlocksAtFeet(self, 'diamond_block')

    def update(self):
        if self.state == 'init':
            print(self.test.tick())
            """
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
            self.actuation.place_block((0, 1, 0))"""
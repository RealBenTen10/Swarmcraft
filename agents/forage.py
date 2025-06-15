from swarmcraft.agent import Agent
from swarmcraft.btree.manipulation import CheckAllBlocksAtFeet, Dig
from swarmcraft.btree.movement import WalkToPosition


# find an object, and then bring it back to a place
# chunks of diamond blocks, bring them back to a starting point
# collaboratively?

# random wander until you find a diamond block
# bring it back, saying where you found it
# place it in the pile
# repeat

# control here is sort of a mix of btree and state machine for now

class ForageAgent(Agent):
    def __init__(self, pooler, message_server, uid, start_location, env):
        super().__init__(pooler, message_server, uid)
        self.start_location = start_location
        self.state = 'wander'
        self.env = env
        # behavior for walking to a random point in the environment
        self.wander_behavior = WalkToPosition(self, self.env.get_point_in_environment())
        # behavior for checking if any of the blocks around you are wool
        self.look_behavior = CheckAllBlocksAtFeet(self, 'orange_wool')
        # behavior for digging up a block
        self.dig_behavior = Dig(self)

    def update(self):
        if self.state == 'wander':
            if self.wander_behavior.tick() == 'success':
                self.state = 'look'
        elif self.state == 'look':
            status = self.look_behavior.tick()
            if status == 'success':
                self.state = 'dig'
            elif status == 'failure':
                self.wander_behavior = WalkToPosition(self, self.env.get_point_in_environment())
                self.state = 'wander'
        elif self.state == 'dig':
            status = self.dig_behavior.tick()
            if status == 'failure' or not self.sensing.is_digging():
                self.wander_behavior = WalkToPosition(self, self.env.get_point_in_environment())
                self.state = 'wander'
                """
                # WIP - return to dropoff
                self.actuation.select_hotbar(0)
                if self.sensing.get_held_item() is not None:
                    self.state = 'return'
                """

    def reset(self):
        self.pooler.reset_bot_stats(self.bot)
        self.pooler.reset_bot_control(self.bot)
        self.pooler.reset_bot_position(self.bot)
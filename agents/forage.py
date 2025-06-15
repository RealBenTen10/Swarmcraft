from swarmcraft.agent import Agent


# find an object, and then bring it back to a place
# chunks of diamond blocks, bring them back to a starting point
# collaboratively?

# random wander until you find a diamond block, or you find someone saying they found one somewhere
# bring it back, saying where you found it
# place it in the pile
# repeat

# if you come across someone saying they found a block, go to that position and look for a block
# if you don't find one, resume your random wander

class ForageAgent(Agent):
    def __init__(self, pooler, message_server, uid, start_location, env):
        super().__init__(pooler, message_server, uid)
        self.start_location = start_location
        self.state = 'wander'
        self.env = env
        self.wander_behavior = GotoPoint(self.sensing, self.actuation, self.env.get_point_in_environment())

    def update(self):
        if self.state == 'wander':
            if self.wander_behavior.tick() == 'success':
                self.wander_behavior = GotoPoint(self.sensing, self.actuation, self.env.get_point_in_environment())

    def reset(self):
        self.pooler.reset_bot_stats(self.bot)
        self.pooler.reset_bot_control(self.bot)
        self.pooler.reset_bot_position(self.bot)
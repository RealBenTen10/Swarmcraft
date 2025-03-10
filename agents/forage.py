import random

from behaviors.Examples import GotoPoint
from agents.agent import Agent
from server.minecraft_server import minecraft_server
from server.pooler import pooler
from util import add_tuples


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
    def __init__(self, uid, start_location, env):
        super().__init__(uid)
        self.start_location = start_location
        self.state = 'wander'
        self.env = env
        self.wander_behavior = GotoPoint(self.sensing, self.actuation, self.env.get_point_in_environment())

    def update(self):
        if self.state == 'wander':
            if self.wander_behavior.tick() == 'success':
                self.wander_behavior = GotoPoint(self.sensing, self.actuation, self.env.get_point_in_environment())

    def reset(self):
        minecraft_server.send_command(
            f'tp {self.sensing.get_username()} {self.start_location[0] + random.randint(0, 5)} {self.start_location[1]} {self.start_location[2] + random.randint(0, 5)}')
        pooler.reset_bot_stats(self.bot)
        pass
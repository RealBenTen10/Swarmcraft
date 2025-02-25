from agents.agent import Agent

# find an object, and then bring it back to a place
# chunks of diamond blocks, bring them back to a starting point
# collaboratively?

# random wander until you find a diamond block, or you find someone saying they found one somewhere
# bring it back, saying where you found it
# place it in the pile
# repeat

# if you come across someone saying they found a block, go to that position and look for a block
# if you don't find one, resume your random wander

class Forager(Agent):
    def __init__(self, bot, uid):
        super().__init__(bot, uid)

    def update(self):
        pass

    def reset(self):
        pass
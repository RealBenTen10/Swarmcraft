"""
Some miscellaneous behavior nodes that have proven useful while testing/developing foraging and other experiments.
As near as I can figure, best practice for having behavior trees modify agent state (instance vars) seems to be to use getattr to be able to dynamically define the name of the variable to look up.
A little spaghetti but it works, and keeps the behavior trees reasonably decoupled from agents.
"""

from random import random, choice
import math

from swarmcraft import CARDINAL_DIRS
from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import ActionNode


class RandomNode(ActionNode):
    """
    Node for simulating random events
    Rolls a dice at each tick, returning 'success' or 'failure' based on the result
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        if len(args) > 0:
            self.probability = float(args[0])
        else:
            self.randomize_params()

    def randomize_params(self):
        self.probability = random()

    def tick(self) -> str:
        if random() < self.probability:
            return 'success'
        return 'failure'

class ReportPosition(ActionNode):
    """
    Node for having an agent report its position over the internal messenger
    Format is <id> <x> <y> <z>, rotation is omitted
    First argument is the range in which to send the message. If range is omitted, set to random value between 1 and 100.
    Second argument is True/False flag for whether to randomize the range. True randomizes range at initialization to value from 0 to first argument.
    False or omission uses the range provided in first argument.
    Always returns success
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)

        self.max_range = float(args[0]) if len(args) > 0 else random() * 100
        self.range = self.max_range
        self.randomize = args[1] == 'True' if len(args) > 1 else False

        if self.randomize:
            self.randomize_params()

    def randomize_params(self):
        self.range = random() * self.max_range

    def tick(self) -> str:
        p_x, p_y, p_z = self.agent.sensing.get_position()

        if self.range is not None:
            self.agent.actuation.send_global_message(f'{self.agent.id} {p_x} {p_y} {p_z}')
        else:
            self.agent.actuation.send_global_message_ranged(f'{self.agent.id} {p_x} {p_y} {p_z}', self.range)

        return 'success'

class ReceivePositionReport(ActionNode):
    """
    Node for reading in position reports from other agents
    Constructor accepts the name of the instance variable to read into.
    Defaults to 'position_report'.
    When ticked, reads and clears one message from the internal message queue of the format "pos <x> <y> <z>" and writes it to the agent instance variable defined in the constructor.
    If no message could be read, or message does not match expected format, returns failure.
    Otherwise, returns success.
    If the instance variable cannot be found or is of the wrong type, throws an exception.
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.in_pos_name = args[0] if len(args) > 0 else None

        if self.in_pos_name is None:
            self.in_pos_name = 'position_report'
        if not hasattr(self.agent, self.in_pos_name):
            raise AttributeError(f'Agent {self.agent} has no attribute {self.in_pos_name}')
        elif not isinstance(getattr(self.agent, self.in_pos_name), tuple):
            raise TypeError(f'{self.in_pos_name} must be a tuple')
        else:
            self.in_pos = getattr(self.agent, self.in_pos_name)

    def randomize_params(self):
        self.in_pos_name = 'position_report'
        self.in_pos = getattr(self.agent, self.in_pos_name)

    def tick(self) -> str:
        message = self.agent.sensing.pop_message()
        # nothing?
        if message is None:
            return 'failure'
        splits = message.split(' ')
        # expect 4 terms
        if len(splits) != 4:
            return 'failure'
        if splits[0] != 'pos':
            return 'failure'
        # cast and pack
        self.in_pos = (float(splits[1]), float(splits[2]), float(splits[3]))
        return 'success'

class ComparePosition(ActionNode):
    """
    Node for comparing an agent's position with some position tuple in that agent's instance variables.
    Constructor accepts the name of the instance variable to compare against and the direction to compare in.
    Defaults to a random cardinal direction and an instance variable name 'compare_position' if none are provided.
    If the distance between the agent's position and the instance variable (instance variable - position) in the direction provided is greater than 1, returns 'success'.
    Otherwise, returns 'failure'.
    If the instance variable cannot be found, throws an exception.
    """
    def __init__(self, agent: Agent, *args):
        super().__init__(agent)
        self.compare_pos_name = args[0] if len(args) > 0 else None
        self.direction = args[1] if len(args) > 1 else None

        if self.compare_pos_name is None:
            self.compare_pos_name = 'compare_position'
        if not hasattr(self.agent, self.compare_pos_name):
            raise AttributeError(f'Agent {self.agent} has no attribute {self.compare_pos_name}')
        elif not isinstance(getattr(self.agent, self.compare_pos_name), tuple):
            raise TypeError(f'{self.compare_pos_name} must be a tuple')
        else:
            self.compare_pos = getattr(self.agent, self.compare_pos_name)

        if self.direction is None:
            self.randomize_params()
        else:
            try:
                self.direction_vec = CARDINAL_DIRS[self.direction].value
            except KeyError:
                raise ValueError(f'direction must be one of {[i.name for i in CARDINAL_DIRS]}')

    def randomize_params(self):
        self.direction = choice(list(CARDINAL_DIRS)).name
        self.direction_vec = CARDINAL_DIRS[self.direction].value

    def tick(self) -> str:
        pos = self.agent.sensing.get_position()
        # distance from me to him
        diff_x = self.compare_pos[0] - pos[0]
        diff_y = self.compare_pos[1] - pos[1]
        diff_z = self.compare_pos[2] - pos[2]

        # extract the components of the difference vector we care about
        diff_x = diff_x if self.direction_vec[0] != 0 else 0
        diff_y = diff_y if self.direction_vec[1] != 0 else 0
        diff_z = diff_z if self.direction_vec[2] != 0 else 0

        # check if the difference and direction vectors are pointing in the same direction
        sign = lambda x: 1 if x >= 0 else -1
        if sign(diff_x) == sign(self.direction_vec[0]) and sign(diff_y) == sign(self.direction_vec[1]) and sign(diff_z) == sign(self.direction_vec[2]):
            # check if the distance (real distance) is geq 1
            if math.sqrt(diff_x**2 + diff_y**2 + diff_z**2) >= 1:
                return 'success'
        return 'failure'

from typing import override

# implements behavior tree nodes
# inspiration from https://arxiv.org/pdf/1709.00084

# children/parent are other control nodes
class ControlNode(object):
    def __init__(self, children=None, parent=None):
        if children is None:
            children = []
        self.children = children
        self.parent = parent

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def tick(self) -> str:
        return 'success'

# route ticks to children from left -> right until you find a child that has failed or is running
# returns success if all children succeeded
class SequenceNode(ControlNode):
    def __init__(self, children=None):
        super().__init__(children)

    @override
    def tick(self):
        for child in self.children:
            status = child.tick()
            if status == 'running' or status == 'failure':
                return status
        return 'success'

# route ticks left -> right until you find a child that is successful or running
# returns failure only if all children failed
class FallbackNode(ControlNode):
    def __init__(self, children=None):
        super().__init__(children)

    @override
    def tick(self):
        for child in self.children:
            status = child.tick()
            if status == 'running' or status == 'success':
                return status
        return 'failure'

# execute all children left -> right and return success if m children return success
# return failure if len(children) - m + 1 children return failure
# return running otherwise
class ParallelNode(ControlNode):
    def __init__(self, m: int, children=None):
        super().__init__(children)
        if m < 0 or m > len(children):
            raise ValueError('Parallel node threshold must be between 0 and {}'.format(len(children)))
        self.m = m

    @override
    def tick(self):
        statuses = []
        for child in self.children:
            statuses.append(child.tick())
        if statuses.count('success') > self.m:
            return 'success'
        if statuses.count('failure') > len(self.children) - self.m:
            return 'failure'
        return 'running'

# ActionNodes do things whenever they're ticked
# to create your own action, inherit this class and override tick
# tick must return success, running, or failure depending on the action state
# and it should accomplish all its work in as little time as possible
class ActionNode(object):
    def tick(self) -> str:
        # update yourself
        return 'success'

# ConditionNodes evaluate a condition whenever they're ticked
# to create your own condition, inherit this class and override condition()
# condition must return success, running, or failure depending on the condition state
# and it should accomplish all its work in as little time as possible
class ConditionNode(object):
    def condition(self) -> bool:
        # evaluate condition here
        return True

    def tick(self) -> str:
        if self.condition():
            return 'success'
        return 'failure'

# BranchNodes evaluate a condition, then tick either one or another child node
class BranchNode(object):
    def __init__(self, if_node: ControlNode, else_node: ControlNode):
        self.ifNode = if_node
        self.elseNode = else_node

    def condition(self) -> bool:
        return True

    def tick(self) -> str:
        if self.condition():
            return self.ifNode.tick()
        else:
            return self.elseNode.tick()

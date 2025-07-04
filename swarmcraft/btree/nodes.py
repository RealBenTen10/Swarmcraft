from typing import override

# implements behavior tree nodes
# inspiration from https://arxiv.org/pdf/1709.00084

class ControlNode(object):
    """
    Base class for control nodes
    """
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

    def __repr__(self) -> str:
        return 'Control()'
        # format should be "Name(param1, param2, ...)[child1, child2, ...]"

class SequenceNode(ControlNode):
    """
    When ticked, sequence nodes tick their children from left to right until a child is encountered which has failed or is running.
    If all children succeed, returns success.
    Otherwise, returns the status of the last ticked child.
    """
    def __init__(self, children=None):
        super().__init__(children)

    @override
    def tick(self):
        for child in self.children:
            status = child.tick()
            if status == 'running' or status == 'failure':
                return status
        return 'success'

    def __repr__(self) -> str:
        return f"Sequence(){[child for child in self.children]}"

class FallbackNode(ControlNode):
    """
    When ticked, fallback nodes tick their children from left to right until a child is encountered which has succeeded or is running.
    If all children fail, returns failure.
    Otherwise, returns the status of the last ticked child.
    """
    def __init__(self, children=None):
        super().__init__(children)

    @override
    def tick(self):
        for child in self.children:
            status = child.tick()
            if status == 'running' or status == 'success':
                return status
        return 'failure'

    def __repr__(self) -> str:
        return f"Fallback(){[child for child in self.children]}"

class ParallelNode(ControlNode):
    """
    When ticked, parallel nodes tick their children from left to right and return success if m children succeed.
    If len(children) - m + 1 children fail, returns failure.
    Otherwise, returns running.
    """
    def __init__(self, m: int, children=None):
        super().__init__(children)
        if m < 0 or m > len(children):
            raise ValueError('Parallel node threshold must be between 0 and {}'.format(len(children)))
        self.m = m

    @override
    def tick(self):
        success = 0
        failure = 0
        for child in self.children:
            status = child.tick()
            if status == 'success':
                success += 1
            elif status == 'failure':
                failure += 1
        if success > self.m:
            return 'success'
        if failure > len(self.children) - self.m:
            return 'failure'
        return 'running'

    def __repr__(self) -> str:
        return f"Parallel(m={self.m}){[child for child in self.children]}"

class ActionNode(object):
    """
    Action nodes perform actions when they are ticked.
    To implement your own action, inherit from this class and override tick().
    """
    def tick(self) -> str:
        """
        Must return 'success', 'failure' or 'running' depending on the state of the action.
        """
        return 'success'

    def __repr__(self) -> str:
        return 'Action()'

class ConditionNode(object):
    """
    Condition nodes check conditions when they are ticked.
    To implement your own condition, inherit from this class and override condition().
    """
    def condition(self) -> bool:
        return True

    def tick(self) -> str:
        if self.condition():
            return 'success'
        return 'failure'

    def __repr__(self) -> str:
        return 'Condition()'

class BranchNode(object):
    """
    Branch nodes evaluate a condition, then tick either one or the other child based on the result.
    The condition can be defined by inheriting from this class and overriding condition().
    """
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

    def __repr__(self) -> str:
        return f'Branch()[{self.ifNode}, {self.elseNode}]'

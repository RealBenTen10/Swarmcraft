"""
heavy inspo here https://arxiv.org/pdf/2011.03252
genetic programming toolkit for swarmcraft's btrees
"""
import random

from swarmcraft.agent import Agent
from swarmcraft.btree.nodes.base import SequenceNode, FallbackNode, ActionNode, ControlNode

# tree primitives
# control nodes (immutable)
_functions = [SequenceNode, FallbackNode]
# terminals/actions (mutable)
_terminals = []

def add_terminal(terminal: type[ActionNode]):
    """
    Add a terminal to the pool
    """
    _terminals.append(terminal)

def remove_terminal(terminal: type[ActionNode]):
    """
    Remove a terminal from the pool
    """
    _terminals.remove(terminal)

def write_genome(root: ControlNode):
    """
    Tree to genome string
    """
    return root.__repr__()

def bind_tree_to_agent(tree, agent: Agent):
    """
    Bind a behavior tree to an agent
    Depth-first traverse of the tree, setting the agent attribute of each node without children to the given agent
    """
    if hasattr(tree, 'children'):
        for child in tree.children:
            bind_tree_to_agent(child, agent)
    else:
        tree.agent = agent

def generate_maxdepth(depth: int, agent: Agent, min_spread = 1, max_spread = 5):
    """
    Generate a fully populated behavior tree of a given depth, bound to an agent

    @param depth: depth of the tree
    @param agent: agent to bind to terminal nodes
    @param min_spread: minimum number of children of internal nodes
    @param max_spread: maximum number of children of internal nodes
    """
    def build_subtree(d):
        # if at maximum depth, initialize a random terminal
        if d >= depth:
            t = random.choice(_terminals)(agent)
            t.randomize_params()
            return t
        # otherwise, initialize a random control with a random number of children
        n_children = random.randint(min_spread, max_spread)
        children = [build_subtree(d + 1) for _ in range(n_children)]
        node = random.choice(_functions)(children)
        return node
    return build_subtree(0)

def generate_minmax(min_depth: int, max_depth: int, agent: Agent, min_spread = 1, max_spread = 5):
    """
    Generate a behavior tree with a minimum and maximum depth, bound to an agent
    Branches are grown until they reach their minimum
    Once at minimum depth, branches have a 50% chance of being terminated
    Branches are always terminated at maximum depth

    @param min_depth: minimum depth of the tree
    @param max_depth: maximum depth of the tree
    @param agent: agent to bind to terminal nodes
    @param min_spread: minimum number of children of internal nodes
    @param max_spread: maximum number of children of internal nodes
    """
    def build_subtree(d):
        if d < min_depth:
            # if not yet at minimum depth, initialize a random control with a random number of children
            n_children = random.randint(min_spread, max_spread)
            children = [build_subtree(d + 1) for _ in range(n_children)]
            node = random.choice(_functions)(children)
            return node
        if d >= max_depth:
            # if at maximum depth, initialize a random terminal
            t = random.choice(_terminals)(agent)
            t.randomize_params()
            return t
        # roll the dice
        if random.random() < 0.5:
            # if we broke off, add a terminal
            t = random.choice(_terminals)(agent)
            t.randomize_params()
            return t
        # if we didn't, continue as  before
        n_children = random.randint(min_spread, max_spread)
        children = [build_subtree(d + 1) for _ in range(n_children)]
        node = random.choice(_functions)(children)
        return node
    return build_subtree(0)

def crossover(a: ControlNode, b: ControlNode, a_agent: Agent, b_agent: Agent):
    """
    Crossover between two behavior trees
    """
    def get_kth_node_with_parent_and_index(node, k):
        def helper(node, k, count, parent, index_in_parent):
            if node is None:
                return None, None, None, count

            count += 1
            if count == k:
                return node, parent, index_in_parent, count

            if hasattr(node, 'children'):
                for i, child in enumerate(node.children):
                    result, result_parent, child_index, count = helper(
                        child, k, count, node, i
                    )
                    if result is not None:
                        return result, result_parent, child_index, count

            return None, None, None, count

        result, parent, index, _ = helper(node, k, 0, None, None)
        return result, parent, index

    # get subtrees, their parent nodes, and the places of those subtrees in the parent node child lists
    a_sub, a_place, a_index = get_kth_node_with_parent_and_index(a, random.randint(0, a.size() - 1))
    b_sub, b_place, b_index = get_kth_node_with_parent_and_index(b, random.randint(0, b.size() - 1))

    # swap
    a_place.children[a_index] = b_sub
    b_place.children[b_index] = a_sub

    # rebind agents
    bind_tree_to_agent(a, a_agent)
    bind_tree_to_agent(b, b_agent)

def mutate(a: ControlNode, agent: Agent):
    """
    Mutate a behavior tree
    Select a random node in a tree, and replace it with a newly generated subtree of lesser or equivalent depth
    """
    def get_kth_node_with_parent_and_index(node, k):
        def helper(node, k, count, parent, index_in_parent):
            if node is None:
                return None, None, None, count

            count += 1
            if count == k:
                return node, parent, index_in_parent, count

            if hasattr(node, 'children'):
                for i, child in enumerate(node.children):
                    result, result_parent, child_index, count = helper(
                        child, k, count, node, i
                    )
                    if result is not None:
                        return result, result_parent, child_index, count

            return None, None, None, count

        result, parent, index, _ = helper(node, k, 0, None, None)
        return result, parent, index

    # select a subtree, its parent node, and the place of that subtree in the parent node child list
    _, place, index = get_kth_node_with_parent_and_index(a, random.randint(0, a.size() - 1))
    # generate a new subtree
    new = generate_minmax(1, a.size(), None)
    # bind the new subtree to the agent
    bind_tree_to_agent(new, agent)
    # replace the old subtree with the new one
    place.children[index] = new

def read_genome(dna: str, agent: Agent) -> ControlNode:
    # TODO NOT DONE! (recursion)
    """
    Genome string to tree
    """
    # start of the parameters
    param_start_i = dna.find('(')
    depth = 1 # nesting depth
    place = param_start_i + 1
    while depth != 0:
        if dna[place] == '(':
            depth += 1
        elif dna[place] == ')':
            depth -= 1
        place += 1
    children_start_i = place
    depth = 1
    while depth != 0 and place < len(dna):
        if dna[place] == '[':
            depth += 1
        elif dna[place] == ']':
            depth -= 1
        place += 1
    name = dna[0:param_start_i] # node name
    params = dna[param_start_i:children_start_i].strip('()').split(', ') # node parameters
    children = dna[children_start_i:place].strip('[]').split(', ') # node children

    node = None
    for fun in _functions:
        if fun.__name__ in name:
            node = fun() #TODO add children initializers
    if node is not None:
        return node

    for term in _terminals:
        if term.__name__ in name:
            node = term(agent)

    return node

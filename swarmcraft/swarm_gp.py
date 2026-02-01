import random
import copy
from typing import Callable, Type

import swarmcraft.btree.nodes.base as bt
from swarmcraft.agent import Agent

# ============================================================
# 1. PRIMITIVE REGISTRY (AGENT-FREE)
# ============================================================

class ControlPrimitive:
    def __init__(self, cls, min_arity, max_arity):
        self.cls = cls
        self.min_arity = min_arity
        self.max_arity = max_arity


class ActionPrimitive:
    def __init__(self, cls, param_generators=()):
        self.cls = cls
        self.param_generators = param_generators


CONTROL_PRIMITIVES: list[ControlPrimitive] = []
ACTION_PRIMITIVES: list[ActionPrimitive] = []


def register_control(cls: Type[bt.ControlNode], min_arity: int, max_arity: int):
    CONTROL_PRIMITIVES.append(ControlPrimitive(cls, min_arity, max_arity))


def register_action(cls: Type[bt.ActionNode], param_generators=()):
    ACTION_PRIMITIVES.append(ActionPrimitive(cls, param_generators))


# ============================================================
# 2. TREE GENERATION (DEAP genGrow equivalent)
# ============================================================

def generate_grow_tree(min_depth: int, max_depth: int, depth: int = 0):
    height = random.randint(min_depth, max_depth)

    def grow(d):
        stop = d >= height or (d >= min_depth and random.random() < 0.5)
        if stop:
            return _random_action()
        prim = random.choice(CONTROL_PRIMITIVES)
        arity = random.randint(prim.min_arity, prim.max_arity)
        return prim.cls([grow(d + 1) for _ in range(arity)])

    return grow(depth)


def _random_action():
    prim = random.choice(ACTION_PRIMITIVES)
    params = [gen() for gen in prim.param_generators]
    return prim.cls(None, *params)


# ============================================================
# 3. TREE UTILITIES
# ============================================================

def collect_nodes(root, include_root=True):
    nodes = []

    def visit(node, parent=None, index=None):
        if include_root or parent is not None:
            nodes.append((node, parent, index))
        if isinstance(node, bt.ControlNode):
            for i, c in enumerate(node.children):
                visit(c, node, i)

    visit(root)
    return nodes


# ============================================================
# 4. GENETIC OPERATORS (DEAP-EQUIVALENT)
# ============================================================

def cx_one_point(ind1, ind2):
    nodes1 = collect_nodes(ind1, include_root=False)
    nodes2 = collect_nodes(ind2, include_root=False)

    if not nodes1 or not nodes2:
        return ind1, ind2

    n1, p1, i1 = random.choice(nodes1)
    n2, p2, i2 = random.choice(nodes2)

    p1.children[i1], p2.children[i2] = n2, n1
    return ind1, ind2


def mut_grow(ind, min_depth, max_depth):
    nodes = collect_nodes(ind, include_root=True)
    node, parent, index = random.choice(nodes)

    new_subtree = generate_grow_tree(min_depth, max_depth)

    if parent is None:
        return new_subtree

    parent.children[index] = new_subtree
    return ind


# ============================================================
# 5. VARIATION (DEAP varOr)
# ============================================================

def var_or(population, lambda_, cxpb, mutpb, min_depth, max_depth):
    offspring = []

    for _ in range(lambda_):
        op = random.random()

        if op < cxpb:
            p1, p2 = random.sample(population, 2)
            c1, _ = cx_one_point(copy.deepcopy(p1), copy.deepcopy(p2))
            offspring.append(c1)

        elif op < cxpb + mutpb:
            p = copy.deepcopy(random.choice(population))
            offspring.append(mut_grow(p, min_depth, max_depth))

        else:
            offspring.append(copy.deepcopy(random.choice(population)))

    return offspring


# ============================================================
# 6. EVOLUTION STRATEGY (μ + λ)
# ============================================================

def ea_mu_plus_lambda(
    mu: int,
    lambda_: int,
    generations: int,
    min_depth: int,
    max_depth: int,
    cxpb: float,
    mutpb: float,
    evaluate: Callable[[bt.BehaviorTreeNode, int], float],
):
    population = [generate_grow_tree(min_depth, max_depth) for _ in range(mu)]

    for gen in range(generations):
        fitness = {id(ind): evaluate(ind, gen) for ind in population}

        offspring = var_or(
            population,
            lambda_,
            cxpb,
            mutpb,
            min_depth,
            max_depth
        )

        for ind in offspring:
            fitness[id(ind)] = evaluate(ind, gen)

        population = sorted(
            population + offspring,
            key=lambda ind: fitness[id(ind)],
            reverse=True
        )[:mu]

    return population


# ============================================================
# 7. AGENT BINDING (PHENOTYPE)
# ============================================================

def bind_agent(tree, agent: Agent):
    if isinstance(tree, bt.ActionNode):
        tree.agent = agent
    elif isinstance(tree, bt.ControlNode):
        for c in tree.children:
            bind_agent(c, agent)


def instantiate_for_swarm(tree, agents):
    return [
        (lambda t: (bind_agent(t, a), t)[1])(copy.deepcopy(tree))
        for a in agents
    ]


def tree_to_str(node):
    """
    Deterministic string representation of a Behavior Tree,
    including parameters of action nodes.
    """

    # -------------------------------------------------
    # Control nodes
    # -------------------------------------------------
    if isinstance(node, bt.ControlNode):
        name = node.__class__.__name__.replace("Node", "")
        children = ", ".join(tree_to_str(c) for c in node.children)
        return f"{name}({children})"

    # -------------------------------------------------
    # Action nodes (leafs)
    # -------------------------------------------------
    if isinstance(node, bt.ActionNode):
        name = node.__class__.__name__
        # If additional information of ActionNode is needed
        # Explicit parameter extraction
        params = []
        # block color
        if hasattr(node, "color") and node.color != "":
            params.append(f'"{node.color}"')
        # direction to look at
        if hasattr(node, "yaw") and node.yaw != "":
            if node.yaw == -1:
                params.append(f'"random"')
            else:
                params.append(f'"{node.yaw}"')
        # PressDir - currently only "forward"
        if hasattr(node, "key") and node.key != "":
            params.append(f'"{node.key}"')
        # Communication
        if hasattr(node, "message") and node.message != "":
            params.append(f'"{node.message}"')
        if hasattr(node, "message_content") and node.message_content != "":
            params.append(f'"{node.message_content}"')


        if params:
            return f"{name}({', '.join(params)})"

        return name

    # -------------------------------------------------
    # Fallback (should not happen)
    # -------------------------------------------------
    return str(node)



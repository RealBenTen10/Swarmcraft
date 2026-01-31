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
# 2. TREE GENERATION (GENOTYPE)
# ============================================================

def generate_tree(min_depth: int, max_depth: int, depth: int = 0) -> bt.BehaviorTreeNode:
    if depth >= max_depth:
        return _random_action()

    if depth < min_depth or random.random() < 0.6:
        prim = random.choice(CONTROL_PRIMITIVES)
        arity = random.randint(prim.min_arity, prim.max_arity)
        children = [generate_tree(min_depth, max_depth, depth + 1) for _ in range(arity)]
        return prim.cls(children)

    return _random_action()


def _random_action():
    prim = random.choice(ACTION_PRIMITIVES)
    params = [gen() for gen in prim.param_generators]
    return prim.cls(None, *params)  # agent intentionally None


# ============================================================
# 3. TREE UTILITIES
# ============================================================

def _collect_nodes(root):
    nodes = []

    def visit(node, parent=None, index=None):
        nodes.append((node, parent, index))
        if isinstance(node, bt.ControlNode):
            for i, c in enumerate(node.children):
                visit(c, node, i)

    visit(root)
    return nodes


# ============================================================
# 4. GENETIC OPERATORS
# ============================================================

def crossover(a, b):
    na, pa, ia = random.choice(_collect_nodes(a))
    nb, pb, ib = random.choice(_collect_nodes(b))

    if pa is None or pb is None:
        return a, b

    pa.children[ia], pb.children[ib] = nb, na
    return a, b


def mutate(tree, min_depth, max_depth):
    node, parent, index = random.choice(_collect_nodes(tree))
    new_subtree = generate_tree(0, max_depth)

    if parent is None:
        return new_subtree

    parent.children[index] = new_subtree
    return tree


# ============================================================
# 5. AGENT BINDING (PHENOTYPE)
# ============================================================

def bind_agent(tree: bt.BehaviorTreeNode, agent: Agent):
    if isinstance(tree, bt.ActionNode):
        tree.agent = agent
    elif isinstance(tree, bt.ControlNode):
        for c in tree.children:
            bind_agent(c, agent)


def instantiate_for_swarm(tree, agents: list[Agent]):
    instances = []
    for agent in agents:
        t = copy.deepcopy(tree)
        bind_agent(t, agent)
        instances.append(t)
    return instances


# ============================================================
# 6. EVOLUTION LOOP (REPLACES DEAP)
# ============================================================

def evolve(
    population_size: int,
    generations: int,
    min_depth: int,
    max_depth: int,
    evaluate: Callable[[bt.BehaviorTreeNode, int], float],
    cx_prob: float,
    mut_prob: float,
):
    population = [generate_tree(min_depth, max_depth) for _ in range(population_size)]

    for gen in range(generations):
        fitness = [(ind, evaluate(ind, gen)) for ind in population]
        fitness.sort(key=lambda x: x[1], reverse=True)

        elite = fitness[0][0]
        new_pop = [elite]

        while len(new_pop) < population_size:
            p1 = copy.deepcopy(random.choice(fitness)[0])
            p2 = copy.deepcopy(random.choice(fitness)[0])

            if random.random() < cx_prob:
                p1, p2 = crossover(p1, p2)

            if random.random() < mut_prob:
                p1 = mutate(p1, min_depth, max_depth)

            new_pop.append(p1)

        population = new_pop

    return population

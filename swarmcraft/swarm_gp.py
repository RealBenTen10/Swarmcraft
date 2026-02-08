import random
import copy
import csv
import os
import pickle
from pathlib import Path
from typing import Callable, Type, Any, Optional

import swarmcraft.btree.nodes.base as bt
from swarmcraft.agent import Agent


# ============================================================
# 1. PRIMITIVE REGISTRY (AGENT-FREE)
# ============================================================

class ControlPrimitive:
    """
    Represents a control-node primitive usable during tree generation.

    Variables
    ---------
    cls : Type[bt.ControlNode]
        The ControlNode class to instantiate (e.g., SequenceNode, FallbackNode).
    min_arity : int
        Minimum number of children to generate for this control node.
    max_arity : int
        Maximum number of children to generate for this control node.
    """
    def __init__(self, cls: Type[bt.ControlNode], min_arity: int, max_arity: int):
        self.cls = cls
        self.min_arity = min_arity
        self.max_arity = max_arity


class ActionPrimitive:
    """
    Represents an action-node primitive usable as a leaf during tree generation.

    Variables
    ---------
    cls : Type[bt.ActionNode]
        The ActionNode class to instantiate.
    param_generators : tuple[Callable[[], Any], ...]
        Callable generators for ephemeral parameters, each returning one value.
        Example: lambda: "orange_wool"
    """
    def __init__(self, cls: Type[bt.ActionNode], param_generators=()):
        self.cls = cls
        self.param_generators = param_generators


CONTROL_PRIMITIVES: list[ControlPrimitive] = []
ACTION_PRIMITIVES: list[ActionPrimitive] = []


def register_control(cls: Type[bt.ControlNode], min_arity: int, max_arity: int) -> None:
    """
    Register a control-node primitive.

    Variables
    ---------
    cls : Type[bt.ControlNode]
        Control node class to register.
    min_arity : int
        Minimum children count for this primitive.
    max_arity : int
        Maximum children count for this primitive.

    Returns
    -------
    None
    """
    CONTROL_PRIMITIVES.append(ControlPrimitive(cls, min_arity, max_arity))


def register_action(cls: Type[bt.ActionNode], param_generators=()) -> None:
    """
    Register an action-node primitive.

    Variables
    ---------
    cls : Type[bt.ActionNode]
        Action node class to register.
    param_generators : tuple[Callable[[], Any], ...]
        Parameter generators used during random initialization.

    Returns
    -------
    None
    """
    ACTION_PRIMITIVES.append(ActionPrimitive(cls, param_generators))

def reset_primitives() -> None:
    """
    Reset the primitive registries used by GP tree generation.

    This must be called before re-registering primitives when running multiple
    experiments in the same Python process, otherwise primitives accumulate and
    sampling becomes biased due to duplicates.

    Variables
    ---------
    None

    Returns
    -------
    None
    """
    CONTROL_PRIMITIVES.clear()
    ACTION_PRIMITIVES.clear()


# ============================================================
# 2. TREE GENERATION (DEAP genGrow equivalent)
# ============================================================

def generate_grow_tree(min_depth: int, max_depth: int, depth: int = 0) -> bt.BehaviorTreeNode:
    """
    Generate a behavior tree using grow initialization.

    Variables
    ---------
    min_depth : int
        Minimum depth before terminals can appear.
    max_depth : int
        Maximum allowed depth.
    depth : int
        Current recursion depth (used internally).

    Returns
    -------
    bt.BehaviorTreeNode
        Root node of the generated tree.
    """
    height = random.randint(min_depth, max_depth)

    def grow(d: int) -> bt.BehaviorTreeNode:
        stop = d >= height or (d >= min_depth and random.random() < 0.5)
        if stop:
            return _random_action()

        prim = random.choice(CONTROL_PRIMITIVES)
        arity = random.randint(prim.min_arity, prim.max_arity)
        return prim.cls([grow(d + 1) for _ in range(arity)])

    return grow(depth)


def _random_action() -> bt.ActionNode:
    """
    Instantiate a random action node with ephemeral parameters.

    Returns
    -------
    bt.ActionNode
        Action node instance with agent set to None and parameters sampled.
    """
    prim = random.choice(ACTION_PRIMITIVES)
    params = [gen() for gen in prim.param_generators]
    return prim.cls(None, *params)


# ============================================================
# 3. TREE UTILITIES
# ============================================================

def collect_nodes(root: bt.BehaviorTreeNode, include_root: bool = True):
    """
    Collect nodes in a tree, including parent references and child indices.

    Variables
    ---------
    root : bt.BehaviorTreeNode
        Tree root to traverse.
    include_root : bool
        If True, includes root in the returned list.

    Returns
    -------
    list[tuple[bt.BehaviorTreeNode, Optional[bt.ControlNode], Optional[int]]]
        Tuples: (node, parent, index_in_parent_children)
    """
    nodes = []

    def visit(node, parent=None, index=None):
        if include_root or parent is not None:
            nodes.append((node, parent, index))
        if isinstance(node, bt.ControlNode):
            for i, c in enumerate(node.children):
                visit(c, node, i)

    visit(root)
    return nodes


def tree_length(node: bt.BehaviorTreeNode) -> int:
    """
    Compute total number of nodes in the tree (including leaves).

    Variables
    ---------
    node : bt.BehaviorTreeNode
        Root of the tree.

    Returns
    -------
    int
        Total node count. Action nodes count as 1 node each.
        Additionally, action parameters (e.g. "orange_wool") are counted
        as terminal leaves by adding +1 per non-empty parameter attribute.
    """
    if isinstance(node, bt.ControlNode):
        return 1 + sum(tree_length(c) for c in node.children)

    if isinstance(node, bt.ActionNode):
        # count the action itself
        n = 1

        # count ephemeral terminals as leafs (as requested)
        # this maps your current conventions:
        # - color, yaw, key, message, message_content
        for attr in ("color", "yaw", "key", "message", "message_content"):
            if hasattr(node, attr):
                val = getattr(node, attr)
                # treat "" and None as absent
                if val is not None and val != "":
                    n += 1
        return n

    return 1


def tree_max_depth(node: bt.BehaviorTreeNode) -> int:
    """
    Compute maximum depth of a tree.

    Variables
    ---------
    node : bt.BehaviorTreeNode
        Root of the tree.

    Returns
    -------
    int
        Maximum depth, where a single leaf node has depth 1.
    """
    if isinstance(node, bt.ControlNode) and node.children:
        return 1 + max(tree_max_depth(c) for c in node.children)
    return 1


# ============================================================
# 4. GENETIC OPERATORS
# ============================================================

def cx_one_point(ind1: bt.BehaviorTreeNode, ind2: bt.BehaviorTreeNode):
    """
    One-point subtree crossover.

    Variables
    ---------
    ind1 : bt.BehaviorTreeNode
        First individual.
    ind2 : bt.BehaviorTreeNode
        Second individual.

    Returns
    -------
    tuple[bt.BehaviorTreeNode, bt.BehaviorTreeNode]
        Individuals after subtree swap.
    """
    nodes1 = collect_nodes(ind1, include_root=False)
    nodes2 = collect_nodes(ind2, include_root=False)

    if not nodes1 or not nodes2:
        return ind1, ind2

    n1, p1, i1 = random.choice(nodes1)
    n2, p2, i2 = random.choice(nodes2)

    p1.children[i1], p2.children[i2] = n2, n1
    return ind1, ind2


def mut_grow(ind: bt.BehaviorTreeNode, min_depth: int, max_depth: int):
    """
    Subtree mutation by replacement with a newly generated grow subtree.

    Variables
    ---------
    ind : bt.BehaviorTreeNode
        Individual to mutate.
    min_depth : int
        Minimum depth of newly generated subtree.
    max_depth : int
        Maximum depth of newly generated subtree.

    Returns
    -------
    bt.BehaviorTreeNode
        Mutated individual (may be a new root).
    """
    nodes = collect_nodes(ind, include_root=True)
    _, parent, index = random.choice(nodes)

    new_subtree = generate_grow_tree(min_depth, max_depth)

    if parent is None:
        return new_subtree

    parent.children[index] = new_subtree
    return ind


# ============================================================
# 5. VARIATION (DEAP varOr)
# ============================================================

def var_or(population, lambda_, cxpb, mutpb, min_depth, max_depth):
    """
    DEAP-style varOr operator.

    Variables
    ---------
    population : list[bt.BehaviorTreeNode]
        Parent population.
    lambda_ : int
        Number of offspring to generate.
    cxpb : float
        Probability of crossover.
    mutpb : float
        Probability of mutation.
    min_depth : int
        Minimum depth for generated mutation subtree.
    max_depth : int
        Maximum depth for generated mutation subtree.

    Returns
    -------
    list[bt.BehaviorTreeNode]
        Offspring individuals.
    """
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
# SELECTION
# ============================================================

def tournament_selection(individuals, fitness, mu, tournsize):
    """
    Tournament survivor selection.

    Variables
    ---------
    individuals : list[bt.BehaviorTreeNode]
        Pool to select from (usually parents + offspring).
    fitness : dict[int, float]
        Mapping id(individual) -> fitness value.
    mu : int
        Number of survivors to select.
    tournsize : int
        Tournament size (number of aspirants sampled each draw).

    Returns
    -------
    list[bt.BehaviorTreeNode]
        Selected survivors (deep-copied).
    """
    selected = []
    for _ in range(mu):
        aspirants = random.sample(individuals, tournsize)
        winner = max(aspirants, key=lambda ind: fitness[id(ind)])
        selected.append(copy.deepcopy(winner))
    return selected


def select_elites(individuals, fitness, k):
    """
    Elitism selection: copy k best individuals unchanged.

    Variables
    ---------
    individuals : list[bt.BehaviorTreeNode]
        Pool to select from (usually parents + offspring).
    fitness : dict[int, float]
        Mapping id(individual) -> fitness value.
    k : int
        Number of elites.

    Returns
    -------
    list[bt.BehaviorTreeNode]
        Elite individuals (deep-copied).
    """
    return [
        copy.deepcopy(ind)
        for ind in sorted(individuals, key=lambda i: fitness[id(i)], reverse=True)[:k]
    ]


# ============================================================
# LOGGING & CHECKPOINTING
# ============================================================

def _ensure_logging_dirs(logging_dir: Path) -> tuple[Path, Path]:
    """
    Ensure that the logging directory and its subdirectories exist.

    Variables
    ---------
    logging_dir : Path
        Base directory where logs and populations are written.

    Returns
    -------
    tuple[Path, Path]
        (csv_path, populations_dir)
    """
    logging_dir.mkdir(parents=True, exist_ok=True)
    populations_dir = logging_dir / "populations"
    populations_dir.mkdir(parents=True, exist_ok=True)
    csv_path = logging_dir / "gp_log.csv"
    return csv_path, populations_dir



def _init_csv(csv_path: Path) -> None:
    """
    Initialize the CSV file with a header if it does not exist.

    Variables
    ---------
    csv_path : Path
        Path to the CSV log file.

    Returns
    -------
    None
    """
    if csv_path.exists():
        return
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["generation", "individual", "tree_length", "max_depth", "fitness"])


def log_generation(csv_path: Path, gen: int, individuals: list[bt.BehaviorTreeNode], fitness: dict[int, float]) -> None:
    """
    Append per-individual logging rows for one generation to CSV.

    Variables
    ---------
    csv_path : Path
        CSV file path.
    gen : int
        Current generation index.
    individuals : list[bt.BehaviorTreeNode]
        Individuals to log (commonly parents + offspring or survivors).
    fitness : dict[int, float]
        Mapping id(individual) -> fitness value.

    Returns
    -------
    None
    """
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        for ind in individuals:
            writer.writerow([
                gen,
                tree_to_str(ind),
                tree_length(ind),
                tree_max_depth(ind),
                fitness[id(ind)],
            ])


def save_population(checkpoint_path: Path, population: list[bt.BehaviorTreeNode], gen: int, meta: dict[str, Any]) -> None:
    """
    Save a population checkpoint to disk.

    Variables
    ---------
    checkpoint_path : Path
        Output path for the checkpoint file.
    population : list[bt.BehaviorTreeNode]
        The current population to save.
    gen : int
        Generation index of this checkpoint.
    meta : dict[str, Any]
        Metadata (EA parameters) needed to resume consistently.

    Returns
    -------
    None
    """
    payload = {
        "gen": gen,
        "population": copy.deepcopy(population),
        "meta": meta,
    }
    with open(checkpoint_path, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_population(checkpoint_path: Path) -> tuple[int, list[bt.BehaviorTreeNode], dict[str, Any]]:
    """
    Load a population checkpoint from disk.

    Variables
    ---------
    checkpoint_path : Path
        Path to a checkpoint file created by save_population().

    Returns
    -------
    tuple
        (gen, population, meta)
    """
    with open(checkpoint_path, "rb") as f:
        payload = pickle.load(f)

    return payload["gen"], payload["population"], payload.get("meta", {})


# ============================================================
# 6. EVOLUTION STRATEGY (μ + λ)  [MAIN LOOP]
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
    tournsize: int,
    n_elites: int,
    logging_dir: Path,
    resume_from: Optional[Path] = None,
):
    """
    μ+λ genetic programming loop with CSV logging and checkpointing.

    Variables
    ---------
    mu : int
        Number of survivors (population size).
    lambda_ : int
        Number of offspring generated per generation.
    generations : int
        Total generations to run.
    min_depth : int
        Minimum depth for grow generation and mutation subtrees.
    max_depth : int
        Maximum depth for grow generation and mutation subtrees.
    cxpb : float
        Crossover probability in var_or.
    mutpb : float
        Mutation probability in var_or.
    evaluate : Callable[[bt.BehaviorTreeNode, int], float]
        Fitness evaluation function.
    tournsize : int
        Tournament size for survivor selection.
    n_elites : int
        Number of elite individuals copied unchanged each generation.
    logging_dir : Path
        Directory where CSV and checkpoint files are stored.
    resume_from : Optional[Path]
        If provided, load population and generation from this checkpoint
        and continue from there.

    Returns
    -------
    list[bt.BehaviorTreeNode]
        Final population after evolution.
    """
    csv_path, populations_dir = _ensure_logging_dirs(Path(logging_dir))
    _init_csv(csv_path)

    meta = {
        "mu": mu,
        "lambda_": lambda_,
        "min_depth": min_depth,
        "max_depth": max_depth,
        "cxpb": cxpb,
        "mutpb": mutpb,
        "tournsize": tournsize,
        "n_elites": n_elites,
    }

    if resume_from is not None:
        start_gen, population, loaded_meta = load_population(Path(resume_from))
        # meta is stored to help you verify consistency on resume
        meta.update({"loaded_meta": loaded_meta, "resumed_from": str(resume_from)})
        gen0 = start_gen + 1
    else:
        population = [generate_grow_tree(min_depth, max_depth) for _ in range(mu)]
        gen0 = 0
        # save initial population checkpoint
        save_population(populations_dir / "gen_0.pkl", population, 0, meta)
        save_population(populations_dir / "latest.pkl", population, 0, meta)

    for gen in range(gen0, generations):
        # evaluate parents
        fitness = {id(ind): evaluate(ind, gen) for ind in population}

        # create offspring
        offspring = var_or(
            population,
            lambda_,
            cxpb,
            mutpb,
            min_depth,
            max_depth
        )

        # evaluate offspring
        for ind in offspring:
            fitness[id(ind)] = evaluate(ind, gen)

        # log all evaluated individuals this generation
        log_generation(csv_path, gen, population + offspring, fitness)

        # elitism
        elites = select_elites(population + offspring, fitness, n_elites)

        # tournament selection
        survivors = tournament_selection(
            population + offspring,
            fitness,
            mu - n_elites,
            tournsize
        )

        population = elites + survivors

        # checkpoint population after selection
        save_population(populations_dir / f"gen_{gen}.pkl", population, gen, meta)
        save_population(populations_dir / "latest.pkl", population, gen, meta)

    return population


# ============================================================
# 7. AGENT BINDING (PHENOTYPE)
# ============================================================

def bind_agent(tree, agent: Agent) -> None:
    """
    Bind a behavior tree instance to an agent by setting agent references
    on every ActionNode.

    Variables
    ---------
    tree : bt.BehaviorTreeNode
        Tree to bind.
    agent : Agent
        Agent to attach to ActionNodes.

    Returns
    -------
    None
    """
    if isinstance(tree, bt.ActionNode):
        tree.agent = agent
    elif isinstance(tree, bt.ControlNode):
        for c in tree.children:
            bind_agent(c, agent)


def instantiate_for_swarm(tree, agents):
    """
    Instantiate one tree per agent by deep-copying the genotype and binding.

    Variables
    ---------
    tree : bt.BehaviorTreeNode
        Genotype tree (agent-free).
    agents : list[Agent]
        Agents to bind to.

    Returns
    -------
    list[bt.BehaviorTreeNode]
        One bound tree instance per agent.
    """
    instances = []
    for a in agents:
        t = copy.deepcopy(tree)
        bind_agent(t, a)
        instances.append(t)
    return instances


def tree_to_str(node):
    """
    Deterministic string representation of a behavior tree, including selected
    action parameters (used for logging).

    Variables
    ---------
    node : bt.BehaviorTreeNode
        Tree root.

    Returns
    -------
    str
        String representation.
    """
    if isinstance(node, bt.ControlNode):
        name = node.__class__.__name__.replace("Node", "")
        children = ", ".join(tree_to_str(c) for c in node.children)
        return f"{name}({children})"

    if isinstance(node, bt.ActionNode):
        name = node.__class__.__name__
        params = []

        if hasattr(node, "color") and node.color not in ("", None):
            params.append(f'"{node.color}"')

        if hasattr(node, "yaw") and node.yaw not in ("", None):
            params.append('"random"' if node.yaw == -1 else f'"{node.yaw}"')

        if hasattr(node, "key") and node.key not in ("", None):
            params.append(f'"{node.key}"')

        if hasattr(node, "message") and node.message not in ("", None):
            params.append(f'"{node.message}"')

        if hasattr(node, "message_content") and node.message_content not in ("", None):
            params.append(f'"{node.message_content}"')

        return f"{name}({', '.join(params)})" if params else name

    return str(node)

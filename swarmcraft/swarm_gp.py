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
# TREE SANITIZATION UTILITY
# ============================================================

def sanitize_tree(node: bt.BehaviorTreeNode) -> bt.BehaviorTreeNode:
    """
    Recursively clean execution state (e.g., agent references, status)
    from a behavior tree so it behaves exactly like a freshly generated
    subtree from the normal grow method.
    """
    if hasattr(node, "agent"):
        node.agent = None
    if hasattr(node, "status"):
        node.status = None

    if isinstance(node, bt.ControlNode) and hasattr(node, "children"):
        for child in node.children:
            sanitize_tree(child)

    return node


# ============================================================
# CURRICULUM LEARNING SKILLS
# ============================================================

SKILL_LIBRARY: list[bt.BehaviorTreeNode] = []


def save_skill(
    tree: bt.BehaviorTreeNode,
    skill_name: str,
    skills_dir: str = "skills",
) -> Path:
    """
    Save a learned behavior tree into the curriculum-learning skill library.

    Parameters
    ----------
    tree : bt.BehaviorTreeNode
        Tree to store.
    skill_name : str
        Output filename without extension.
    skills_dir : str
        Directory where skills are stored.

    Returns
    -------
    Path
        Saved file path.
    """
    skill_dir = Path(skills_dir)
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_path = skill_dir / f"{skill_name}.pkl"

    try:
        # Deepcopy and sanitize to remove any active agent states before pickling
        tree_copy = copy.deepcopy(tree)
        sanitize_tree(tree_copy)

        with open(skill_path, "wb") as f:
            pickle.dump(tree_copy, f, protocol=pickle.HIGHEST_PROTOCOL)

        print(f"Saved skill: {skill_path}")

    except Exception as e:
        print(f"Failed to save skill '{skill_name}': {e}")

    return skill_path


def load_skill(skill_path: str | Path) -> Optional[bt.BehaviorTreeNode]:
    """
    Load a single skill tree from disk.
    """
    try:
        with open(skill_path, "rb") as f:
            tree = pickle.load(f)

        if not isinstance(tree, bt.BehaviorTreeNode):
            raise TypeError(
                f"Skill file does not contain a BehaviorTreeNode: {skill_path}"
            )

        return tree

    except FileNotFoundError:
        print(f"Skill file not found: {skill_path}")

    except pickle.UnpicklingError:
        print(f"Corrupted skill file: {skill_path}")

    except Exception as e:
        print(f"Failed loading skill {skill_path}: {e}")

    return None


def load_skill_library(skill_paths: list[str | Path]) -> None:
    """
    Load multiple skills into the global curriculum library.
    """
    SKILL_LIBRARY.clear()
    print(f"Loading {len(skill_paths)} skills:")
    for path in skill_paths:
        skill = load_skill(path)

        if skill is not None:
            # Ensure loaded skill is pristine before adding to library
            sanitize_tree(skill)
            SKILL_LIBRARY.append(skill)

            # String splitting safely handles paths
            file_name = str(path).split(os.sep)[-1].split(".")[0]
            print(f" - {file_name}: {skill}")


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
    param_attrs : Optional[tuple[str, ...]]
        Attribute names on the instantiated ActionNode corresponding to each generator
        in the same order as param_generators. Recommended for multi-parameter actions.
        If None, attributes are inferred best-effort.
    """

    def __init__(self, cls: Type[bt.ActionNode], param_generators=(), param_attrs=None):
        self.cls = cls
        self.param_generators = tuple(param_generators) if param_generators else tuple()
        self.param_attrs = tuple(param_attrs) if param_attrs else None


CONTROL_PRIMITIVES: list[ControlPrimitive] = []
ACTION_PRIMITIVES: list[ActionPrimitive] = []
ACTION_PRIMITIVE_BY_CLS: dict[Type[bt.ActionNode], ActionPrimitive] = {}


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


def register_action(cls: Type[bt.ActionNode], param_generators=(), param_attrs=None) -> None:
    """
    Register an action-node primitive.

    Variables
    ---------
    cls : Type[bt.ActionNode]
        Action node class to register.
    param_generators : tuple[Callable[[], Any], ...]
        Parameter generators used during random initialization.
    param_attrs : Optional[tuple[str, ...]]
        Attribute names corresponding to param_generators (recommended if >1 parameter).

    Returns
    -------
    None
    """
    prim = ActionPrimitive(cls, param_generators, param_attrs)
    ACTION_PRIMITIVES.append(prim)
    ACTION_PRIMITIVE_BY_CLS[cls] = prim

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
    ACTION_PRIMITIVE_BY_CLS.clear()


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


def sample_skill_subtree() -> Optional[bt.BehaviorTreeNode]:
    """
    Return a sanitized deepcopy of a random stored skill.
    """
    if not SKILL_LIBRARY:
        return None

    # Deepcopy and sanitize so it acts identically to a grow-generated subtree
    skill = copy.deepcopy(random.choice(SKILL_LIBRARY))
    return sanitize_tree(skill)


def generate_mutation_subtree(
    min_depth: int,
    max_depth: int,
) -> bt.BehaviorTreeNode:
    """
    Generate a mutation subtree.
    Either inject a previously learned skill or generate a random grow subtree.
    """

    if (
            SKILL_LIBRARY
            and random.random() < len(SKILL_LIBRARY) / len(ACTION_PRIMITIVES)
    ):
        skill = sample_skill_subtree()

        if skill is not None:
            print("Injected skill: ", skill)
            return skill

        print("No skill available. Prob at: ", len(SKILL_LIBRARY) / len(ACTION_PRIMITIVES), " and skills: ",
              SKILL_LIBRARY)

    print("normal mutation")
    return generate_grow_tree(min_depth, max_depth)

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


# Action-node parameter attribute names that are commonly used
# this is different from the registered action nodes
# these values are stored in the action nodes and are not equivilant to the action node parameters
_KNOWN_TERMINAL_ATTRS = ("color", "yaw", "key", "message", "message_content", "direction")

def _get_action_primitive(node: bt.ActionNode) -> Optional[ActionPrimitive]:
    """
    Return the registered ActionPrimitive for a concrete ActionNode instance.
    """
    prim = ACTION_PRIMITIVE_BY_CLS.get(node.__class__)
    if prim is not None:
        return prim

    # fallback if instances use subclasses/proxies
    for cls, p in ACTION_PRIMITIVE_BY_CLS.items():
        if isinstance(node, cls):
            return p
    return None


def _infer_param_attrs(action: bt.ActionNode, prim: ActionPrimitive) -> list[str]:
    """
    Determine the attribute names on `action` corresponding to the generators in `prim`.

    Rules:
      - If prim.param_attrs is provided, use it verbatim.
      - Else, prefer known terminal attr names present on the instance.
      - Else (rare), attempt a conservative fallback:
          - for a single-parameter action: pick the only "non-empty" public attribute
            excluding obvious non-parameter fields, if that yields a unique candidate.

    Note:
      For multi-parameter actions, strongly prefer passing param_attrs during registration.
    """
    if prim.param_attrs is not None:
        return list(prim.param_attrs)

    present = [a for a in _KNOWN_TERMINAL_ATTRS if hasattr(action, a)]
    if not prim.param_generators:
        return []

    if len(prim.param_generators) == 1:
        if present:
            return present[:1]

        # Conservative fallback: attempt to find a single plausible parameter attribute.
        ignore = {"agent"}
        candidates = []
        for k, v in vars(action).items():
            if k in ignore or k.startswith("_"):
                continue
            if v is None or v == "":
                continue
            candidates.append(k)
        if len(candidates) == 1:
            return candidates
        return []

    # Multi-parameter: best-effort mapping only if enough known attrs are present
    if len(present) >= len(prim.param_generators):
        return present[:len(prim.param_generators)]
    return []


def collect_mutation_points(root: bt.BehaviorTreeNode):
    """
    Collect mutation points consisting of:
      - ("node", node, parent, index)
      - ("terminal", action_node, parent, index, param_index, attr_name, generator, prim)

    This allows mutation to choose uniformly among:
      - control/action nodes (subtrees), and
      - instantiated parameters of action nodes (terminals).
    """
    points = []

    def visit(node, parent=None, index=None):
        points.append(("node", node, parent, index))

        if isinstance(node, bt.ControlNode):
            for i, c in enumerate(node.children):
                visit(c, node, i)
            return

        if isinstance(node, bt.ActionNode):
            prim = _get_action_primitive(node)
            if prim is None or not prim.param_generators:
                return

            attrs = _infer_param_attrs(node, prim)
            attrs = attrs[:len(prim.param_generators)]

            for j, attr in enumerate(attrs):
                if not hasattr(node, attr):
                    continue
                val = getattr(node, attr)
                if val is None or val == "":
                    continue
                points.append(("terminal", node, parent, index, j, attr, prim.param_generators[j], prim))

    visit(root)
    return points


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

        # count ephemeral terminals as leafs
        # this maps current conventions using _KNOWN_TERMINAL_ATTRS list
        for attr in _KNOWN_TERMINAL_ATTRS:
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

    Mutation that samples uniformly from both:
      - nodes (control + action, including root) and
      - terminals (instantiated action parameters)

    If a node is selected:
      - replace the subtree at that node with a new grow tree

    If a terminal is selected:
      - resample that parameter using its registered generator and rebuild the action node
        to keep constructor logic consistent.

    This follows DEAP's philosophy (mutation by replacing a randomly chosen slice),
    extended to include terminals as selectable points.

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
    points = collect_mutation_points(ind)
    if not points:
        return ind

    choice = random.choice(points)
    # --- Terminal mutation (parameter resample) ---
    if choice[0] == "terminal":
        _, action, parent, index, param_i, attr, gen, prim = choice

        current = getattr(action, attr, None)
        new_val = gen()
        # avoid no-op when generator can return same value
        for _ in range(10):
            if new_val != current:
                break
            new_val = gen()

        attrs = _infer_param_attrs(action, prim)
        attrs = attrs[:len(prim.param_generators)]
        if not attrs:
            # fallback: mutate in-place (best effort)
            setattr(action, attr, new_val)
            return ind

        # Rebuild from current parameters, with one replaced
        params = [getattr(action, a, None) for a in attrs]
        if 0 <= param_i < len(params):
            params[param_i] = new_val
            new_action = prim.cls(None, *params)

            if parent is None:
                return new_action
            parent.children[index] = new_action
            return ind

        setattr(action, attr, new_val)
        return ind

    # --- Node mutation (subtree replacement) ---
    _, _node, parent, index = choice
    new_subtree = generate_mutation_subtree(
        min_depth,
        max_depth
    )
    # new_subtree = generate_grow_tree(min_depth, max_depth) # old logic without skills

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
    print("Loading population from: ", checkpoint_path)
    with open(checkpoint_path, "rb") as f:
        payload = pickle.load(f)
    print("Population loaded: ", payload["population"])

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
    resume_from: Path,
):
    """
    μ+λ genetic programming loop with CSV logging and checkpointing.

    This matches DEAP's eaMuPlusLambda structure:
      - evaluate parents
      - produce offspring via varOr
      - evaluate offspring
      - select next population from parents + offspring (μ survivors), optionally with elites

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

    print("resume from: ", resume_from)

    # Tracks the single best individual seen across the whole run, deep-
    # copied at the moment it's found. This has to happen BEFORE
    # elitism/tournament selection run: both select_elites() and
    # tournament_selection() return copy.deepcopy()'d individuals, so by
    # the time population = elites + survivors is assembled, none of
    # those objects' id()s match anything in that generation's `fitness`
    # dict anymore -- a fitness.get(id(ind)) lookup against `population`
    # after selection silently misses for every individual. Snapshotting
    # best_ever here, against `combined` (still the original, fitness-
    # keyed objects), sidesteps that identity mismatch entirely rather
    # than trying to sort around it afterward.
    best_ever: Optional[bt.BehaviorTreeNode] = None
    best_ever_fitness: float = float("-inf")

    if resume_from is not None:
        print("Loading old population")
        start_gen, population, loaded_meta = load_population(Path(resume_from))
        # meta is stored to help you verify consistency on resume
        meta.update({"loaded_meta": loaded_meta, "resumed_from": str(resume_from)})
        gen0 = start_gen + 1
    else:
        print("Initializing new population")
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

        combined = population + offspring

        # log all evaluated individuals this generation
        log_generation(csv_path, gen, combined, fitness)

        # Snapshot this generation's best individual before selection
        # deep-copies anything and identities stop matching `fitness`.
        gen_best = max(combined, key=lambda ind: fitness[id(ind)])
        gen_best_fitness = fitness[id(gen_best)]
        if gen_best_fitness > best_ever_fitness:
            best_ever_fitness = gen_best_fitness
            best_ever = copy.deepcopy(gen_best)

        # elitism
        elites = select_elites(combined, fitness, n_elites)

        # tournament selection
        survivors = tournament_selection(
            combined,
            fitness,
            mu - n_elites,
            tournsize
        )

        population = elites + survivors

        # checkpoint population after selection
        save_population(populations_dir / f"gen_{gen}.pkl", population, gen, meta)
        save_population(populations_dir / "latest.pkl", population, gen, meta)

    # Guarantee population[0] is the true best individual seen during the
    # whole run. This is strictly stronger than "best of the final
    # generation" (which is all n_elites>=1 elitism actually promises,
    # and even that can be beaten by a later generation's individual that
    # scored well due to environment noise rather than being genuinely
    # better) -- and unlike a post-hoc sort, it doesn't depend on
    # `population`'s post-selection objects sharing identity with
    # `fitness`, which (per the note above) they don't.
    if best_ever is not None:
        population[0] = best_ever
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

        if hasattr(node, "direction") and node.direction not in ("", None):
            params.append(f'"{node.direction}"')

        if hasattr(node, "key") and node.key not in ("", None):
            params.append(f'"{node.key}"')

        if hasattr(node, "message") and node.message not in ("", None):
            params.append(f'"{node.message}"')

        if hasattr(node, "message_content") and node.message_content not in ("", None):
            params.append(f'"{node.message_content}"')

        return f"{name}({', '.join(params)})" if params else name

    return str(node)
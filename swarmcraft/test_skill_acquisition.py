#!/usr/bin/env python3

import copy
import random
from pathlib import Path

import swarmcraft.btree.nodes.base as bt

from swarmcraft import BlockTypes

from swarmcraft.btree.nodes.actuation import (
    StartDig,
    Rotate,
    PressDir,
    ReleaseDir,
    SendMessage,
)

from swarmcraft.btree.nodes.sensing import (
    SenseBlock,
    GotMessage,
)

from swarm_gp import (
    register_control,
    register_action,
    reset_primitives,

    generate_grow_tree,
    mut_grow,

    tree_to_str,
    tree_length,

    ea_mu_plus_lambda,

    ACTION_PRIMITIVES,
    ACTION_PRIMITIVE_BY_CLS,

    save_skill,
    load_skill,
    load_skill_library,

    SKILL_LIBRARY,
)

import swarm_gp


# ============================================================
# Pretty Printing
# ============================================================

_PRINT_ATTRS = (
    "color",
    "yaw",
    "direction",
    "key",
    "message",
    "message_content",
)


def tree_to_str_verbose(node):
    if isinstance(node, bt.ControlNode):
        name = node.__class__.__name__.replace("Node", "")
        children = ", ".join(tree_to_str_verbose(c) for c in node.children)
        return f"{name}({children})"

    if isinstance(node, bt.ActionNode):
        name = node.__class__.__name__

        kv = []

        for attr in _PRINT_ATTRS:
            if hasattr(node, attr):
                val = getattr(node, attr)

                if val is not None and val != "":
                    kv.append(f"{attr}={val!r}")

        return f"{name}({', '.join(kv)})" if kv else name

    return str(node)


# ============================================================
# Helpers
# ============================================================

def _find_action_prim(action_cls):
    prim = ACTION_PRIMITIVE_BY_CLS.get(action_cls)

    if prim is not None:
        return prim

    for p in ACTION_PRIMITIVES:
        if p.cls is action_cls:
            return p

    raise KeyError(action_cls)


def make_action(action_cls):
    prim = _find_action_prim(action_cls)

    params = [
        gen()
        for gen in prim.param_generators
    ]

    return action_cls(None, *params)


def make_all_actions_tree():
    """
    Creates a deterministic skill tree that contains
    every action at least once.
    """

    leaves = [
        make_action(StartDig),
        make_action(SenseBlock),
        make_action(Rotate),
        make_action(PressDir),
        make_action(ReleaseDir),
        make_action(SendMessage),
        make_action(GotMessage),
        make_action(Rotate),
    ]

    return bt.SequenceNode([
        bt.FallbackNode([
            leaves[0],
            leaves[1]
        ]),
        bt.SequenceNode([
            bt.FallbackNode([
                leaves[2],
                leaves[3]
            ]),
            bt.SequenceNode([
                bt.FallbackNode([
                    leaves[4],
                    leaves[5]
                ]),
                bt.FallbackNode([
                    leaves[6],
                    leaves[7]
                ])
            ])
        ])
    ])


# ============================================================
# Primitive Registration
# ============================================================

def register_real_primitives():

    reset_primitives()

    register_control(
        bt.SequenceNode,
        2,
        2
    )

    register_control(
        bt.FallbackNode,
        2,
        2
    )

    register_action(
        StartDig,
        param_generators=[
            lambda: random.choice([
                BlockTypes.BLUE_WOOL.value,
                BlockTypes.ORANGE_WOOL.value
            ])
        ]
    )

    register_action(
        SenseBlock,
        param_generators=[
            lambda: random.choice([
                BlockTypes.BLUE_WOOL.value,
                BlockTypes.ORANGE_WOOL.value,
                BlockTypes.BEDROCK.value
            ])
        ]
    )

    register_action(
        Rotate,
        param_generators=[
            lambda: random.choice([
                90,
                45,
                -1,
                -45,
                -90
            ])
        ]
    )

    register_action(PressDir)

    register_action(ReleaseDir)

    register_action(
        SendMessage,
        param_generators=[
            lambda: random.choice([1, 2])
        ]
    )

    register_action(
        GotMessage,
        param_generators=[
            lambda: random.choice([1, 2])
        ]
    )


# ============================================================
# Fitness
# ============================================================

def random_fitness(_tree, _gen):
    return random.random()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    random.seed(12)

    register_real_primitives()

    print("\n" + "=" * 80)
    print("TEST 1: SAVE / LOAD SKILL")
    print("=" * 80)

    skill_tree = make_all_actions_tree()

    save_skill(
        skill_tree,
        "foraging_test"
    )

    loaded_skill = load_skill(
        "skills/foraging_test.pkl"
    )

    assert loaded_skill is not None

    print("\nOriginal Skill:")
    print(tree_to_str_verbose(skill_tree))

    print("\nLoaded Skill:")
    print(tree_to_str_verbose(loaded_skill))

    assert (
        tree_to_str_verbose(skill_tree)
        ==
        tree_to_str_verbose(loaded_skill)
    )

    print("\nPASS")


    print("\n" + "=" * 80)
    print("TEST 2: MULTIPLE SKILLS")
    print("=" * 80)

    save_skill(
        generate_grow_tree(1, 3),
        "skill_a"
    )

    save_skill(
        generate_grow_tree(1, 3),
        "skill_b"
    )

    load_skill_library([
        "skills/foraging_test.pkl",
        "skills/skill_a.pkl",
        "skills/skill_b.pkl",
    ])

    print(f"\nLoaded Skills: {len(SKILL_LIBRARY)}")

    assert len(SKILL_LIBRARY) == 3

    for i, skill in enumerate(SKILL_LIBRARY):
        print(
            f"\nSkill {i}:"
        )
        print(
            tree_to_str_verbose(skill)
        )

    print("\nPASS")


    print("\n" + "=" * 80)
    print("TEST 3: SKILL INJECTION")
    print("=" * 80)

    swarm_gp.SKILL_INJECTION_PROB = 1.0

    parent = generate_grow_tree(
        min_depth=1,
        max_depth=2
    )

    print("\nParent:")
    print(tree_to_str_verbose(parent))

    mutated = mut_grow(
        copy.deepcopy(parent),
        min_depth=1,
        max_depth=2
    )

    print("\nMutated:")
    print(tree_to_str_verbose(mutated))

    skill_strings = {
        tree_to_str_verbose(skill)
        for skill in SKILL_LIBRARY
    }

    mutated_str = tree_to_str_verbose(mutated)

    found_skill = any(
        s in mutated_str
        for s in skill_strings
    )

    print(f"\nInjected Skill Detected: {found_skill}")

    assert found_skill

    print("\nPASS")


    print("\n" + "=" * 80)
    print("TEST 4: REPEATED SKILL INJECTION")
    print("=" * 80)

    hits = 0

    for _ in range(100):

        individual = generate_grow_tree(
            1,
            2
        )

        individual = mut_grow(
            individual,
            1,
            2
        )

        txt = tree_to_str_verbose(individual)

        if any(
            tree_to_str_verbose(skill) in txt
            for skill in SKILL_LIBRARY
        ):
            hits += 1

    print(
        f"\nSkill injections: {hits}/100"
    )

    assert hits > 0

    print("\nPASS")


    print("\n" + "=" * 80)
    print("TEST 5: EVOLVE SKILL")
    print("=" * 80)

    skill_copy = copy.deepcopy(
        SKILL_LIBRARY[0]
    )

    before = tree_to_str_verbose(
        skill_copy
    )

    print("\nBefore:")
    print(before)

    evolved = skill_copy

    for _ in range(10):
        evolved = mut_grow(
            evolved,
            1,
            3
        )

    after = tree_to_str_verbose(
        evolved
    )

    print("\nAfter:")
    print(after)

    assert before != after

    print("\nPASS")


    print("\n" + "=" * 80)
    print("TEST 6: FULL CURRICULUM EA")
    print("=" * 80)

    skill_signature = tree_to_str_verbose(
        SKILL_LIBRARY[0]
    )

    def curriculum_fitness(tree, gen):

        txt = tree_to_str_verbose(tree)

        if skill_signature in txt:
            return 10.0

        return 0.0

    population = ea_mu_plus_lambda(
        mu=20,
        lambda_=20,
        generations=10,
        min_depth=1,
        max_depth=3,
        cxpb=0.45,
        mutpb=0.45,
        evaluate=curriculum_fitness,
        tournsize=3,
        n_elites=1,
        logging_dir=Path(
            "./logging/test_curriculum"
        ),
        resume_from=None,
    )

    fitnesses = [
        curriculum_fitness(ind, 0)
        for ind in population
    ]

    best_idx = max(
        range(len(population)),
        key=lambda i: fitnesses[i]
    )

    best = population[best_idx]

    print("\nBest Individual:")
    print(tree_to_str_verbose(best))

    print(
        "\nBest Fitness:",
        curriculum_fitness(best, 0)
    )

    assert skill_signature in tree_to_str_verbose(best)

    print("\nPASS")


    print("\n" + "=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
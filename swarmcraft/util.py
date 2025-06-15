"""
utility functions
"""
import operator
from typing import Any

import numpy as np
from numpy import floating

CARDINAL_DIRS = {
    'n': (1, 0, 0),
    'e': (0, 0, 1),
    's': (-1, 0, 0),
    'w': (0, 0, -1),
    'ne': (0.707, 0, 0.707),
    'nw': (0.707, 0, -0.707),
    'se': (-0.707, 0, 0.707),
    'sw': (-0.707, 0, -0.707)
}

def dist_sqr(a, b) -> floating[Any]:
    a = np.array(a)
    b = np.array(b)
    if a.shape != b.shape:
        raise ValueError("Cannot compute distance between arrays of different shapes")
    return np.sum((a - b) ** 2.0)

def dist(a, b) -> float:
    return np.sqrt(dist_sqr(a, b))

def add_tuples(a, b):
    return tuple(map(operator.add, a, b))

def multiply_tuples(a, b):
    return tuple(map(operator.mul, a, b))
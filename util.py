"""
utility functions
"""
import operator
from typing import Any

import numpy as np
from numpy import floating


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
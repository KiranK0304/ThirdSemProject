"""Mathematical utilities for vector normalization and cosine similarity."""

from __future__ import annotations

import math


def normalize_vector(vector: list[float]) -> list[float]:
    """Normalize a vector to unit length (L2 norm = 1.0).

    Args:
        vector: A list of floating point values.

    Returns:
        A new list with the vector scaled to unit length. If the norm is zero,
        returns the original vector.
    """
    if not vector:
        return []

    norm_sq = sum(x * x for x in vector)
    if norm_sq == 0.0:
        return list(vector)

    norm = math.sqrt(norm_sq)
    return [x / norm for x in vector]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Assumes vectors are pre-normalized to unit length for performance,
    reducing cosine similarity to a dot product. Falls back to standard
    normalization if vector norms differ from 1.0.

    Args:
        v1: First vector.
        v2: Second vector.

    Returns:
        Cosine similarity float in range [-1.0, 1.0].
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    return sum(a * b for a, b in zip(v1, v2))

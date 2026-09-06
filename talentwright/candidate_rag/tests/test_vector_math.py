"""Tests for vector math utilities."""

import math
import pytest

from talentwright.candidate_rag.services.vector_math import cosine_similarity
from talentwright.candidate_rag.services.vector_math import normalize_vector


def test_normalize_vector():
    vec = [3.0, 4.0]
    normed = normalize_vector(vec)
    assert len(normed) == 2
    assert math.isclose(normed[0], 0.6, rel_tol=1e-5)
    assert math.isclose(normed[1], 0.8, rel_tol=1e-5)

    # L2 norm must be 1.0
    magnitude = math.sqrt(sum(x * x for x in normed))
    assert math.isclose(magnitude, 1.0, rel_tol=1e-5)


def test_normalize_empty_or_zero():
    assert normalize_vector([]) == []
    assert normalize_vector([0.0, 0.0]) == [0.0, 0.0]


def test_cosine_similarity():
    # Identical unit vectors
    v1 = normalize_vector([1.0, 2.0, 3.0])
    assert math.isclose(cosine_similarity(v1, v1), 1.0, rel_tol=1e-5)

    # Orthogonal vectors
    v_x = [1.0, 0.0]
    v_y = [0.0, 1.0]
    assert math.isclose(cosine_similarity(v_x, v_y), 0.0, abs_tol=1e-5)

    # Opposite vectors
    v_pos = [1.0, 0.0]
    v_neg = [-1.0, 0.0]
    assert math.isclose(cosine_similarity(v_pos, v_neg), -1.0, rel_tol=1e-5)


def test_cosine_similarity_edge_cases():
    assert cosine_similarity([], [1.0, 2.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0

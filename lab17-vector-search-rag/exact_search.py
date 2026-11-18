"""Exact cosine top-k search and recall calculation for benchmark vectors."""

import numpy as np


def exact_top_k(vectors: np.ndarray, query: np.ndarray, k: int = 20) -> np.ndarray:
    scores = vectors @ query
    return np.argsort(-scores)[:k]


def recall_percent(found: np.ndarray, exact: np.ndarray) -> float:
    return len(set(map(int, found)) & set(map(int, exact))) / len(exact) * 100.0

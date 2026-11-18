"""Reproducible, local 5,000-vector IVF versus HNSW-style benchmark.

This educational comparison does not represent a MongoDB Atlas benchmark.
Atlas HNSW/IVF support requires a configured deployment and is reported separately.
"""

import csv
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import MiniBatchKMeans

from exact_search import exact_top_k, recall_percent
from generate_dataset import COUNT, OUT, SEED, generate

N_QUERIES = 100
K = 20


class IVFIndex:
    def __init__(self, clusters: int = 100, probes: int = 5) -> None:
        self.clusters = clusters
        self.probes = probes

    def build(self, vectors: np.ndarray) -> None:
        start = time.perf_counter()
        model = MiniBatchKMeans(
            n_clusters=self.clusters,
            random_state=SEED,
            n_init=1,
            batch_size=512,
            max_iter=40,
        )
        self.labels = model.fit_predict(vectors)
        self.centroids = model.cluster_centers_
        self.buckets = [np.flatnonzero(self.labels == i) for i in range(self.clusters)]
        self.vectors = vectors
        self.build_seconds = time.perf_counter() - start

    def search(self, query: np.ndarray) -> tuple[np.ndarray, int]:
        centroid_ids = np.argsort(-(self.centroids @ query))[: self.probes]
        candidates = np.concatenate([self.buckets[int(i)] for i in centroid_ids])
        selected = candidates[np.argsort(-(self.vectors[candidates] @ query))[:K]]
        return selected, len(candidates)


class HNSWStyleIndex:
    """Single-layer NSW graph used as a transparent, educational HNSW proxy."""

    def __init__(self, neighbors: int = 12, construction_candidates: int = 120, ef_search: int = 64) -> None:
        self.neighbors = neighbors
        self.construction_candidates = construction_candidates
        self.ef_search = ef_search

    def build(self, vectors: np.ndarray) -> None:
        start = time.perf_counter()
        self.vectors = vectors
        graph = [set() for _ in range(len(vectors))]
        for node in range(1, len(vectors)):
            candidates = np.random.default_rng(node + SEED).choice(
                node, size=min(node, self.construction_candidates), replace=False
            )
            nearest = candidates[np.argsort(-(vectors[candidates] @ vectors[node]))[: self.neighbors]]
            for other in nearest:
                other = int(other)
                graph[node].add(other)
                graph[other].add(node)
        self.graph = graph
        self.build_seconds = time.perf_counter() - start

    def search(self, query: np.ndarray) -> tuple[np.ndarray, int]:
        import heapq

        rng = np.random.default_rng(SEED)
        frontier = []
        visited: set[int] = set()
        best: list[tuple[float, int]] = []
        for entry in rng.choice(len(self.vectors), size=8, replace=False):
            entry = int(entry)
            score = float(self.vectors[entry] @ query)
            heapq.heappush(frontier, (-score, entry))
            heapq.heappush(best, (score, entry))
            visited.add(entry)
        while frontier:
            negative_score, node = heapq.heappop(frontier)
            score = -negative_score
            if len(best) >= self.ef_search and score < best[0][0]:
                break
            for neighbor in self.graph[node]:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                neighbor_score = float(self.vectors[neighbor] @ query)
                if len(best) < self.ef_search or neighbor_score > best[0][0]:
                    heapq.heappush(frontier, (-neighbor_score, neighbor))
                    heapq.heappush(best, (neighbor_score, neighbor))
                    if len(best) > self.ef_search:
                        heapq.heappop(best)
        found = [index for _, index in sorted(best, reverse=True)[:K]]
        return np.asarray(found, dtype=np.int64), len(visited)


def _queries(vectors: np.ndarray) -> list[np.ndarray]:
    rng = np.random.default_rng(SEED + 1)
    chosen = rng.choice(len(vectors), N_QUERIES, replace=False)
    queries = []
    for index in chosen:
        query = vectors[index] + rng.normal(0, 0.025, size=vectors.shape[1]).astype(np.float32)
        query /= np.linalg.norm(query)
        queries.append(query)
    return queries


def _measure(
    name: str,
    index,
    queries: list[np.ndarray],
    ground_truth: list[np.ndarray],
    exact_latency_ms: float,
) -> dict:
    latencies = []
    recalls = []
    examined = []
    for query, exact in zip(queries, ground_truth):
        started = time.perf_counter()
        found, count = index.search(query)
        latencies.append(time.perf_counter() - started)
        recalls.append(recall_percent(found, exact))
        examined.append(count)
    return {
        "index": name,
        "dataset": "local educational benchmark (not Atlas)",
        "build_time_seconds": index.build_seconds,
        "avg_query_latency_ms": float(np.mean(latencies) * 1000),
        "recall_at_20_percent": float(np.mean(recalls)),
        "avg_vectors_examined": float(np.mean(examined)),
        "queries": len(queries),
        "documents": COUNT,
        "dimensions": int(index.vectors.shape[1]),
        "exact_search_latency_ms": exact_latency_ms,
    }


def _measure_exact(
    vectors: np.ndarray, queries: list[np.ndarray]
) -> tuple[list[np.ndarray], float, dict]:
    exact_results = []
    latencies = []
    recalls = []
    for query in queries:
        started = time.perf_counter()
        found = exact_top_k(vectors, query, K)
        latencies.append(time.perf_counter() - started)
        exact_results.append(found)
        recalls.append(recall_percent(found, found))

    if any(recall != 100.0 for recall in recalls):
        raise RuntimeError("Exact brute-force results did not achieve 100% self-recall.")
    average_latency_ms = float(np.mean(latencies) * 1000)
    exact_result = {
        "index": "ExactBruteForce",
        "dataset": "local educational benchmark (not Atlas)",
        "build_time_seconds": 0.0,
        "avg_query_latency_ms": average_latency_ms,
        "recall_at_20_percent": float(np.mean(recalls)),
        "avg_vectors_examined": float(len(vectors)),
        "queries": len(queries),
        "documents": len(vectors),
        "dimensions": int(vectors.shape[1]),
        "exact_search_latency_ms": average_latency_ms,
    }
    return exact_results, average_latency_ms, exact_result


def run() -> list[dict]:
    dataset_path = OUT / "benchmark_dataset.jsonl"
    vectors_path = OUT / "benchmark_vectors.npy"
    if not dataset_path.exists() or not vectors_path.exists():
        _, vectors = generate()
    else:
        vectors = np.load(vectors_path)
    if vectors.shape != (COUNT, 384):
        raise ValueError(f"Expected a (5000, 384) matrix, found {vectors.shape}.")
    queries = _queries(vectors)
    ground_truth, exact_latency_ms, exact_result = _measure_exact(vectors, queries)
    results = [exact_result]
    for index in (IVFIndex(), HNSWStyleIndex()):
        index.build(vectors)
        results.append(
            _measure(type(index).__name__, index, queries, ground_truth, exact_latency_ms)
        )

    OUT.mkdir(exist_ok=True)
    with (OUT / "comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    with (Path("comparison.csv")).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    (OUT / "benchmark_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    report_lines = [
        "# Lab 17.2 — Local Benchmark Report",
        "",
        "> This is a local educational benchmark, not an Atlas or production HNSW result. "
        "Vectors are reproducible 384-D hashed lexical features, not learned semantic embeddings.",
        "",
        f"Dataset: {COUNT:,} documents × 384 dimensions; queries: {N_QUERIES}; exact ground truth: cosine top-{K}.",
        "",
        "Exact search evaluates cosine similarity against all 5,000 vectors for each query. "
        "Recall@20 = |index top-20 ∩ exact brute-force top-20| / 20 × 100.",
        "",
        "| Index | Build time (s) | Avg latency (ms) | Recall@20 (%) | Avg vectors examined |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in results:
        report_lines.append(
            f"| {row['index']} | {row['build_time_seconds']:.4f} | "
            f"{row['avg_query_latency_ms']:.4f} | {row['recall_at_20_percent']:.2f} | "
            f"{row['avg_vectors_examined']:.1f} |"
        )
    report_lines.extend([
        "",
        "IVF restricts scanning to selected centroid buckets; increasing probes typically trades "
        "latency for recall. The graph-based HNSW-style traversal produced higher recall in this run "
        "with its measured graph build and query costs. Actual ranking can change with dataset, "
        "parameters, hardware, and implementation.",
        "",
        "The HNSW-style implementation is a single-layer educational NSW proxy, not a production "
        "HNSW library. No Atlas connection was configured, so Atlas index capability and live "
        "$vectorSearch measurements were not verified. No IVF Atlas index is claimed.",
        "",
        f"Mean exact brute-force query latency across {N_QUERIES} queries: "
        f"{exact_latency_ms:.4f} ms. The CSV also records this exact-search latency "
        "for each index row.",
        "",
        "See `latency_vs_recall.png` for the measured exact and approximate latency/recall points.",
        "",
    ])
    report_text = "\n".join(report_lines)
    (OUT / "comparison_report.md").write_text(report_text, encoding="utf-8")
    Path("comparison_report.md").write_text(report_text, encoding="utf-8")

    figure, axis = plt.subplots(figsize=(8, 5))
    for result in results:
        axis.scatter(
            result["avg_query_latency_ms"],
            result["recall_at_20_percent"],
            s=90,
            label=result["index"],
        )
        axis.annotate(
            result["index"],
            (result["avg_query_latency_ms"], result["recall_at_20_percent"]),
            xytext=(6, 6),
            textcoords="offset points",
        )
    axis.set_xlabel("Average query latency (ms; local benchmark)")
    axis.set_ylabel("Recall@20 (%)")
    axis.set_title("Local Exact, IVF and HNSW-style Search")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "latency_vs_recall.png", dpi=160)
    plt.close(figure)
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run()

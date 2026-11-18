# Lab 17.2 — Local Benchmark Report

> This is a local educational benchmark, not an Atlas or production HNSW result. Vectors are reproducible 384-D hashed lexical features, not learned semantic embeddings.

Dataset: 5,000 documents × 384 dimensions; queries: 100; exact ground truth: cosine top-20.

Exact search evaluates cosine similarity against all 5,000 vectors for each query. Recall@20 = |index top-20 ∩ exact brute-force top-20| / 20 × 100.

| Index | Build time (s) | Avg latency (ms) | Recall@20 (%) | Avg vectors examined |
|---|---:|---:|---:|---:|
| ExactBruteForce | 0.0000 | 1.9028 | 100.00 | 5000.0 |
| IVFIndex | 0.6341 | 0.1999 | 53.35 | 260.6 |
| HNSWStyleIndex | 0.3121 | 1.2756 | 92.20 | 634.2 |

IVF restricts scanning to selected centroid buckets; increasing probes typically trades latency for recall. The graph-based HNSW-style traversal produced higher recall in this run with its measured graph build and query costs. Actual ranking can change with dataset, parameters, hardware, and implementation.

The HNSW-style implementation is a single-layer educational NSW proxy, not a production HNSW library. No Atlas connection was configured, so Atlas index capability and live $vectorSearch measurements were not verified. No IVF Atlas index is claimed.

Mean exact brute-force query latency across 100 queries: 1.9028 ms. The CSV also records this exact-search latency for each index row.

See `latency_vs_recall.png` for the measured exact and approximate latency/recall points.

"""Measure latency of each FraudQueryService method on the real databases -> output/latency_report.md"""
import os
import statistics
import time

from lab16_2.fraud_service import FraudQueryService

RUNS = 50


def measure(fn):
    for _ in range(5):          # warm-up
        fn()
    samples = []
    for _ in range(RUNS):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000)
    samples.sort()
    return {"avg": statistics.mean(samples), "p95": samples[int(0.95 * len(samples)) - 1],
            "min": samples[0], "max": samples[-1]}


def main():
    svc = FraudQueryService()
    rows = [("get_transaction (MongoDB)", lambda: svc.get_transaction("TXN-1001")),
            ("get_user_profile (Cassandra)", lambda: svc.get_user_profile("U1")),
            ("detect_fraud_rings 1 hop (Neo4j)", lambda: svc.detect_fraud_rings("U1", 1)),
            ("detect_fraud_rings 2 hops (Neo4j)", lambda: svc.detect_fraud_rings("U1", 2)),
            ("detect_fraud_rings 3 hops (Neo4j)", lambda: svc.detect_fraud_rings("U1", 3)),
            ("analyze() merged workflow", lambda: svc.analyze("U1", "TXN-1001"))]
    lines = ["# Latency report (Lab 16.2)", "",
             f"Measured on this machine, {RUNS} runs per method after 5 warm-up runs, values in ms.", "",
             "| Method | avg | p95 | min | max |", "|---|---|---|---|---|"]
    for name, fn in rows:
        m = measure(fn)
        lines.append(f"| {name} | {m['avg']:.2f} | {m['p95']:.2f} | {m['min']:.2f} | {m['max']:.2f} |")
    lines += ["", "## Typical characteristics (documented expectation)",
              "- MongoDB indexed lookups: about 2-5 ms.",
              "- Cassandra single-partition time-ordered reads: about 3-8 ms.",
              "- Neo4j traversals: about 10 ms for 1 hop, growing to about 500 ms for 3 hops on a dense graph "
              "(cost grows with the branching factor per hop). Our seed graph is tiny, so it stays low here.",
              "- The merged analyze() call costs roughly the SUM of the three because they run sequentially; "
              "running them concurrently would bring it down to the slowest backend (Neo4j)."]
    report = "\n".join(lines)
    print(report)
    os.makedirs("output", exist_ok=True)
    with open("output/latency_report.md", "w") as f:
        f.write(report + "\n")
    svc.close()


if __name__ == "__main__":
    main()

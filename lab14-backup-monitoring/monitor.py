#!/usr/bin/env python3
"""
Lab 14.1 - MongoDB monitoring dashboard.

Collects: connection count, opcounters, WiredTiger cache stats, replica set status.
Prints a table, appends it to a log file every N seconds, prints WARNING when
  * cache hit ratio < 80 %          (--cache-threshold)
  * replication lag  > 10 seconds   (--lag-threshold)
and (extension) POSTs the alert to a Slack/Discord webhook (--webhook or $WEBHOOK_URL).
"""
import argparse
import datetime
import os
import time

import requests
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from tabulate import tabulate

DEFAULT_URI = "mongodb://localhost:27017/?directConnection=true"


def get_metrics(client):
    ss = client.admin.command("serverStatus")
    cache = ss["wiredTiger"]["cache"]

    requested = cache.get("pages requested from the cache", 0)
    read_into = cache.get("pages read into cache", 0)
    # hit ratio = share of page requests served from memory (no disk read needed)
    hit_ratio = 100.0 * (1 - read_into / requested) if requested else 100.0

    m = {
        "connections_current": ss["connections"]["current"],
        "connections_available": ss["connections"]["available"],
        "opcounters": ss["opcounters"],
        "cache_bytes_in_cache": cache.get("bytes currently in the cache", 0),
        "cache_max_bytes": cache.get("maximum bytes configured", 0),
        "cache_pages_requested": requested,
        "cache_pages_read_into": read_into,
        "cache_hit_ratio": hit_ratio,
        "repl": None,
        "repl_lag": None,
    }

    try:  # replica set status (only if the server is part of a replica set)
        rs = client.admin.command("replSetGetStatus")
        members = rs.get("members", [])
        primary = next((x for x in members if x["stateStr"] == "PRIMARY"), None)
        lag = 0.0
        if primary:
            for x in members:
                if x["stateStr"] == "SECONDARY":
                    diff = (primary["optimeDate"] - x["optimeDate"]).total_seconds()
                    lag = max(lag, diff)
        m["repl"] = {"set": rs["set"], "members": members}
        m["repl_lag"] = lag
    except OperationFailure:
        pass  # standalone server
    return m


def build_report(m):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        ["Connections (current)", m["connections_current"]],
        ["Connections (available)", m["connections_available"]],
    ]
    for k, v in m["opcounters"].items():
        rows.append([f"opcounter: {k}", v])
    rows += [
        ["WT cache bytes in cache", m["cache_bytes_in_cache"]],
        ["WT cache max bytes", m["cache_max_bytes"]],
        ["WT pages requested from cache", m["cache_pages_requested"]],
        ["WT pages read into cache", m["cache_pages_read_into"]],
        ["WT cache hit ratio (%)", f"{m['cache_hit_ratio']:.2f}"],
    ]
    if m["repl"]:
        for x in m["repl"]["members"]:
            rows.append([f"RS member {x['name']}", x["stateStr"]])
        rows.append(["Replication lag (s)", f"{m['repl_lag']:.1f}"])
    else:
        rows.append(["Replica set", "not a replica set member"])
    return f"=== MongoDB metrics @ {ts} ===\n" + tabulate(rows, headers=["Metric", "Value"], tablefmt="grid")


def check_alerts(m, cache_thr, lag_thr):
    alerts = []
    if m["cache_hit_ratio"] < cache_thr:
        alerts.append(f"WARNING: cache hit ratio {m['cache_hit_ratio']:.2f}% is below {cache_thr}%")
    if m["repl_lag"] is not None and m["repl_lag"] > lag_thr:
        alerts.append(f"WARNING: replication lag {m['repl_lag']:.1f}s exceeds {lag_thr}s")
    return alerts


def send_webhook(url, message):
    """Slack uses 'text', Discord uses 'content' - send both."""
    payload = {"text": message, "content": message}
    try:
        r = requests.post(url, json=payload, timeout=5)
        r.raise_for_status()
        print(f"   [webhook] alert sent (HTTP {r.status_code})")
    except requests.RequestException as e:
        print(f"   [webhook] FAILED to send alert: {e}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--uri", default=DEFAULT_URI)
    p.add_argument("--interval", type=int, default=30, help="seconds between samples (default 30)")
    p.add_argument("--iterations", type=int, default=0, help="0 = run forever")
    p.add_argument("--log", default="metrics.log")
    p.add_argument("--cache-threshold", type=float, default=80.0)
    p.add_argument("--lag-threshold", type=float, default=10.0)
    p.add_argument("--webhook", default=os.environ.get("WEBHOOK_URL"))
    a = p.parse_args()

    client = MongoClient(a.uri, serverSelectionTimeoutMS=5000)
    n = 0
    try:
        while True:
            n += 1
            m = get_metrics(client)
            report = build_report(m)
            alerts = check_alerts(m, a.cache_threshold, a.lag_threshold)
            print(report)
            with open(a.log, "a") as f:
                f.write(report + "\n")
                for al in alerts:
                    f.write(al + "\n")
            for al in alerts:
                print(al)
                if a.webhook:
                    send_webhook(a.webhook, al)
            if a.iterations and n >= a.iterations:
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


if __name__ == "__main__":
    main()

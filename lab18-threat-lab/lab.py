import os, time, random, statistics, json, datetime as dt, sys
from pymongo import MongoClient, ASCENDING, UpdateOne
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from neo4j import GraphDatabase
import networkx as nx

N = int(os.getenv("N_THREATS", 100000))
OUT = "/output"; os.makedirs(OUT, exist_ok=True)
DOCKER_URL = os.getenv("DOCKER_URL", "https://hub.docker.com/r/yourname/threat-lab")
random.seed(42)

def retry(fn, what, tries=60, delay=5):
    for i in range(tries):
        try: return fn()
        except Exception as e:
            print(f"waiting for {what} ({i+1}/{tries}): {str(e)[:60]}", flush=True); time.sleep(delay)
    sys.exit(f"{what} unavailable")

# ------------------------------------------------------------ data
TYPES = ["malware", "phishing", "ddos", "bruteforce", "portscan", "exfiltration"]
SOURCES = [f"src-{i:03d}" for i in range(50)]
RING = SOURCES[:6]                      # sources behaving like a noisy / false-positive ring
RING_TARGETS = [f"host-{i:03d}" for i in range(15)]
TARGETS = [f"host-{i:03d}" for i in range(300)]
NOW = dt.datetime.utcnow().replace(microsecond=0)

def make(i, tag="t"):
    ring = random.random() < 0.12
    src = random.choice(RING if ring else SOURCES[6:])
    tgt = random.choice(RING_TARGETS) if ring and random.random() < 0.9 else random.choice(TARGETS)
    ts = NOW - dt.timedelta(seconds=random.randint(0, 30 * 86400))
    fp = random.random() < (0.8 if src in RING else 0.02)
    return dict(id=f"{tag}{i}", src=src, target=tgt, type=random.choice(TYPES), ts=ts,
                ts_ms=int(ts.timestamp() * 1000), day=ts.strftime("%Y-%m-%d"),
                sev=random.randint(1, 10), fp=fp)

# ------------------------------------------------------------ connections
mongo = retry(lambda: (lambda c: (c.admin.command("ping"), c)[1])(MongoClient("mongo", 27017)), "MongoDB")
mdb = mongo["threatdb"]
cas_cluster = retry(lambda: Cluster(["cassandra"]).connect(), "Cassandra", tries=80)
cas = cas_cluster
neo = retry(lambda: (lambda d: (d.verify_connectivity(), d)[1])(GraphDatabase.driver("bolt://neo4j:7687")), "Neo4j")

# ------------------------------------------------------------ schemas
mongo.drop_database("threatdb")
mdb.full_threats.create_index([("from_source", ASCENDING), ("timestamp", ASCENDING)])
mdb.full_threats.create_index([("threat_type", ASCENDING), ("day", ASCENDING)])

cas.execute("CREATE KEYSPACE IF NOT EXISTS threatks WITH replication={'class':'SimpleStrategy','replication_factor':1}")
cas.set_keyspace("threatks")
cas.execute("""CREATE TABLE IF NOT EXISTS threats_by_source (from_source text, ts timestamp, threat_id text,
  target text, threat_type text, severity int, is_fp boolean, day text,
  PRIMARY KEY ((from_source), ts, threat_id)) WITH CLUSTERING ORDER BY (ts DESC, threat_id ASC)""")
cas.execute("""CREATE TABLE IF NOT EXISTS threats_by_type (threat_type text, day text, ts timestamp, threat_id text,
  from_source text, target text, severity int, is_fp boolean,
  PRIMARY KEY ((threat_type, day), ts, threat_id))""")
cas.execute("TRUNCATE threats_by_source"); cas.execute("TRUNCATE threats_by_type")

with neo.session() as s:
    s.run("MATCH (n) DETACH DELETE n")
    s.run("CREATE CONSTRAINT src IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE")
    s.run("CREATE CONSTRAINT tgt IF NOT EXISTS FOR (n:Target) REQUIRE n.id IS UNIQUE")
    s.run("CREATE CONSTRAINT thr IF NOT EXISTS FOR (n:Threat) REQUIRE n.id IS UNIQUE")
    s.run("CREATE INDEX thr_type IF NOT EXISTS FOR (n:Threat) ON (n.threat_type)")

# ------------------------------------------------------------ loaders (reused by insert benchmark)
P_SRC = cas.prepare("INSERT INTO threats_by_source (from_source,ts,threat_id,target,threat_type,severity,is_fp,day) VALUES (?,?,?,?,?,?,?,?)")
P_TYP = cas.prepare("INSERT INTO threats_by_type (threat_type,day,ts,threat_id,from_source,target,severity,is_fp) VALUES (?,?,?,?,?,?,?,?)")
CYPHER_INS = """UNWIND $rows AS r
MERGE (s:Source {id:r.src}) MERGE (g:Target {id:r.target})
CREATE (t:Threat {id:r.id, threat_type:r.type, target:r.target, ts:r.ts_ms, day:r.day, severity:r.sev, fp:r.fp})
CREATE (s)-[:SENT]->(t) CREATE (t)-[:TARGETS]->(g)"""

def mdoc(r): return dict(_id=r["id"], from_source=r["src"], target=r["target"], threat_type=r["type"],
                         timestamp=r["ts"], day=r["day"], severity=r["sev"], is_false_positive=r["fp"])
def mongo_insert(rows):
    mdb.full_threats.insert_many([mdoc(r) for r in rows], ordered=False)
    mdb.threat.bulk_write([UpdateOne({"_id": r["src"]}, {"$push": {"recent_threats": {"$each": [mdoc(r)],
        "$sort": {"timestamp": -1}, "$slice": 50}}, "$inc": {"total": 1}}, upsert=True) for r in rows], ordered=False)
def cas_insert(rows):
    args = [(r["src"], r["ts"], r["id"], r["target"], r["type"], r["sev"], r["fp"], r["day"]) for r in rows]
    execute_concurrent_with_args(cas, P_SRC, args, concurrency=100)
    args = [(r["type"], r["day"], r["ts"], r["id"], r["src"], r["target"], r["sev"], r["fp"]) for r in rows]
    execute_concurrent_with_args(cas, P_TYP, args, concurrency=100)
def neo_insert(rows):
    with neo.session() as s: s.run(CYPHER_INS, rows=rows)

print(f"Generating {N} threats...", flush=True)
data = [make(i) for i in range(N)]
load = {}
for name, fn in [("MongoDB", mongo_insert), ("Cassandra", cas_insert), ("Neo4j", neo_insert)]:
    t0 = time.time()
    for i in range(0, N, 5000): fn(data[i:i + 5000])
    load[name] = round(time.time() - t0, 1); print(f"Loaded {name} in {load[name]}s", flush=True)
# Mongo recent_threats is already capped at 50 per source by $slice.

# ------------------------------------------------------------ benchmark queries
SRC = RING[0]; QTYPE = "phishing"
DAYS = [(NOW - dt.timedelta(days=d)).strftime("%Y-%m-%d") for d in range(31)]
P_H = cas.prepare("SELECT * FROM threats_by_source WHERE from_source=? LIMIT 50")
P_S = cas.prepare("SELECT target, threat_type FROM threats_by_source WHERE from_source=?")
P_D = cas.prepare("SELECT count(*) FROM threats_by_type WHERE threat_type=? AND day=?")

def q1_mongo(): return mdb.threat.find_one({"_id": SRC})["recent_threats"]
def q1_cas(): return list(cas.execute(P_H, [SRC]))
def q1_neo():
    with neo.session() as s: return s.run("MATCH (:Source {id:$s})-[:SENT]->(t:Threat) RETURN t ORDER BY t.ts DESC LIMIT 50", s=SRC).data()
def q2_mongo(): return list(mdb.full_threats.aggregate([{"$match": {"from_source": SRC}},
    {"$group": {"_id": "$target", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}]))
def q2_cas():
    c = {}
    for r in cas.execute(P_S, [SRC]): c[r.target] = c.get(r.target, 0) + 1
    return sorted(c.items(), key=lambda x: -x[1])
def q2_neo():
    with neo.session() as s: return s.run("MATCH (:Source {id:$s})-[:SENT]->(:Threat)-[:TARGETS]->(g:Target) RETURN g.id AS t, count(*) AS n ORDER BY n DESC", s=SRC).data()
def q3_mongo(): return list(mdb.full_threats.aggregate([{"$match": {"threat_type": QTYPE}}, {"$group": {"_id": "$day", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}}]))
def q3_cas(): return [(d, cas.execute(P_D, [QTYPE, d]).one()[0]) for d in DAYS]
def q3_neo():
    with neo.session() as s: return s.run("MATCH (t:Threat {threat_type:$ty}) RETURN t.day AS d, count(*) AS n ORDER BY d", ty=QTYPE).data()

def median_ms(fn, runs=10):
    ts = []
    for _ in range(runs):
        t0 = time.perf_counter(); fn(); ts.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(ts), 2)

BATCH = 1000; ctr = [0]
def ins(fn):
    def run():
        ctr[0] += 1; fn([make(ctr[0] * BATCH + j, f"new{ctr[0]}-") for j in range(BATCH)])
    return run

QN = ["Q1 Threat history (last 50)", "Q2 Target and spread", "Q3 Daily volume analytics", "Q4 Insert 1000 threats (batch)"]
res = {n: {} for n in QN}
for db, fns in [("MongoDB", [q1_mongo, q2_mongo, q3_mongo, ins(mongo_insert)]),
                ("Cassandra", [q1_cas, q2_cas, q3_cas, ins(cas_insert)]),
                ("Neo4j", [q1_neo, q2_neo, q3_neo, ins(neo_insert)])]:
    for n, f in zip(QN, fns):
        res[n][db] = median_ms(f); print(db, n, res[n][db], "ms", flush=True)

# ------------------------------------------------------------ Activity 18.1: graph community detection
with neo.session() as s:
    s.run("""MATCH (a:Source)-[:SENT]->(:Threat)-[:TARGETS]->(g:Target)
             WITH a, g, count(*) AS c WHERE c >= 30 MERGE (a)-[h:HITS]->(g) SET h.c = c""")
    s.run("""MATCH (a:Source)-[:HITS]->(g:Target)<-[:HITS]-(b:Source) WHERE a.id < b.id
             WITH a, b, count(g) AS shared WHERE shared >= 5 MERGE (a)-[r:SUSPICIOUS]->(b) SET r.shared = shared""")
    edges = s.run("MATCH (a:Source)-[r:SUSPICIOUS]->(b:Source) RETURN a.id AS a, b.id AS b, r.shared AS w").data()
G = nx.Graph(); G.add_weighted_edges_from([(e["a"], e["b"], e["w"]) for e in edges])
base = mdb.full_threats.count_documents({"is_false_positive": True}) / max(1, mdb.full_threats.count_documents({}))
communities = []
for comp in nx.connected_components(G):
    m = sorted(comp)
    tot = mdb.full_threats.count_documents({"from_source": {"$in": m}})
    fpc = mdb.full_threats.count_documents({"from_source": {"$in": m}, "is_false_positive": True})
    communities.append(dict(members=m, edges=G.subgraph(m).number_of_edges(), threats=tot, fp=fpc, fp_rate=round(fpc / max(tot, 1), 3)))
print("Communities:", json.dumps(communities), "baseline FP", round(base, 3), flush=True)
json.dump(dict(load=load, results=res, communities=communities, baseline_fp=base), open(f"{OUT}/results.json", "w"), indent=2)

# ------------------------------------------------------------ Lab 18.2 report (PDF)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, PageBreak
ss = getSampleStyleSheet(); H1, H2, B = ss["Heading1"], ss["Heading2"], ss["BodyText"]
def tbl(rows, widths=None):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t
def P(x): return Paragraph(x, B)
win = {}
for n in QN: win[n] = min(res[n], key=res[n].get)
doc = SimpleDocTemplate(f"{OUT}/report.pdf", pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
S = [Paragraph("Comparative Analysis Report: False-Positive Detection in Threat Intelligence", H1),
     P(f"Lab 18.1 and 18.2 - MongoDB vs Cassandra vs Neo4j<br/>Docker image: <b>{DOCKER_URL}</b>"), Spacer(1, 8)]
S += [Paragraph("1. Executive Summary", H2), P(
    f"We loaded {N:,} synthetic threat events from {len(SOURCES)} sources into MongoDB, Cassandra and Neo4j and benchmarked four queries (median of 10 runs). "
    f"Fastest per query: history - {win[QN[0]]}; target spread - {win[QN[1]]}; daily volume - {win[QN[2]]}; insert - {win[QN[3]]}. "
    "Recommendation: use a polyglot design. Cassandra for the high-volume ingest and time-series analytics path, MongoDB for flexible threat detail and fast-display history, "
    "and Neo4j for relationship-based false-positive detection (SUSPICIOUS links between sources and community detection). If only one database can be run, choose MongoDB as the best general-purpose compromise.")]
S += [Paragraph("2. Methodology", H2), P(
    f"Data: {N:,} threats over 30 days, 50 sources (6 form a noisy ring with ~80% false positives, the other 44 ~2%), 300 targets, 6 threat types. "
    "Environment: Docker Compose on a single host, one container each for MongoDB 7, Cassandra 4.1 and Neo4j 5 (community), default configuration, no replication. "
    "Queries: Q1 last 50 threats of a source; Q2 targets hit by a source with counts; Q3 daily count of one threat type over 30 days; Q4 insert of 1000 new threats. Each run 10 times; median reported. "
    f"Bulk load time (s): {load}.")]
S += [Paragraph("3. System Architecture", H2), Preformatted(
"""  +----------------+      +---------------------------+
  | Threat feed    | ---> | Python loader / benchmark |
  | (generator)    |      +-------------+-------------+
  +----------------+          |         |          |
                              v         v          v
                        +---------+ +-----------+ +--------+
                        | MongoDB | | Cassandra | | Neo4j  |
                        +----+----+ +-----------+ +---+----+
                             |   cross-reference      |
                             +<-- communities (SUSPICIOUS)
                                         |
                                  report.pdf / results.json""", style=ss["Code"])]
S += [Paragraph("4. Schema Design", H2), tbl([["Database", "Schema", "Design decision"],
    ["MongoDB", "threat: {_id: source, recent_threats[last 50], total}; full_threats: one doc per threat; index (from_source, timestamp), (threat_type, day)",
     "Embedded last-50 array gives single-read history; full collection keeps everything; compound index for history range queries."],
    ["Cassandra", "threats_by_source PK((from_source), ts DESC, threat_id); threats_by_type PK((threat_type, day), ts, threat_id)",
     "Query-first, denormalised; each query hits one partition. Day in partition key bounds partition size."],
    ["Neo4j", "(Source)-[:SENT]->(Threat)-[:TARGETS]->(Target); (Source)-[:SUSPICIOUS {shared}]->(Source)",
     "SUSPICIOUS edges link sources hitting the same targets heavily (>=30 events per target, >=5 shared targets)."]],
    [60, 260, 220])]
rows = [["Query", "MongoDB (ms)", "Cassandra (ms)", "Neo4j (ms)", "Fastest"]]
for n in QN: rows.append([n] + [res[n][d] for d in ("MongoDB", "Cassandra", "Neo4j")] + [win[n]])
S += [Paragraph("5. Query Performance Comparison (median of 10 runs)", H2), tbl(rows, [170, 80, 85, 80, 80]),
      P(f"Q4 throughput (threats/sec): " + ", ".join(f"{d} {round(BATCH / (res[QN[3]][d] / 1000))}" for d in ("MongoDB", "Cassandra", "Neo4j")))]
S += [Paragraph("6. False-Positive Detection (Activity 18.1)", H2), P(
    f"Neo4j SUSPICIOUS edges found: {len(edges)}. Graph communities (connected components) were cross-referenced with MongoDB threat details. Baseline false-positive rate: {round(base * 100, 1)}%.")]
S += [tbl([["Community members", "Edges", "Threats", "False positives", "FP rate"]] +
          [[", ".join(c["members"]), c["edges"], c["threats"], c["fp"], f'{c["fp_rate"] * 100:.1f}%'] for c in communities] or [["none", 0, 0, 0, "-"]],
          [220, 45, 55, 70, 50]),
      P("A community whose false-positive rate is far above the baseline marks a group of noisy sources that should be tuned or whitelisted.")]
S += [PageBreak(), Paragraph("7. Data Modeling and Ergonomics", H2), tbl([["Aspect", "MongoDB", "Cassandra", "Neo4j"],
    ["Modeling", "Flexible JSON documents, embedding", "Query-driven, duplicate data per query", "Natural graph, relationships first-class"],
    ["Query language", "MQL/aggregation, easy for developers", "CQL, SQL-like but no joins/ad hoc filters", "Cypher, very readable for relationships"],
    ["Ad hoc analytics", "Good", "Poor (needs new table)", "Good for connected data, weaker for big aggregates"],
    ["Learning curve", "Low", "Medium-High (data modeling)", "Medium (graph thinking)"]], [80, 150, 160, 150])]
S += [Paragraph("8. Scalability Assessment (estimates)", H2), tbl([["Scale", "MongoDB", "Cassandra", "Neo4j"],
    ["1M", "1 node, 4 vCPU / 16 GB / 50 GB SSD", "1-3 nodes, 4 vCPU / 16 GB", "1 node, 4 vCPU / 16 GB"],
    ["10M", "Replica set (3 nodes), 8 vCPU / 32 GB, ~500 GB", "3 nodes, 8 vCPU / 32 GB / 1 TB", "1 primary + 2 read replicas (cluster), 8 vCPU / 32-64 GB"],
    ["100M", "Sharded cluster (shard key from_source, hash), 3 shards x 3 replicas, 16 vCPU / 64 GB", "6-12 nodes, 16 vCPU / 64 GB, consistent hashing ring, linear scale", "Large memory nodes (128 GB+) or composite databases/Fabric; write scaling is hardest"]],
    [40, 170, 170, 160]),
    P("Horizontal scaling: MongoDB uses sharding (mongos, config servers) with replica sets; Cassandra is masterless with a token ring and virtual nodes, adding nodes scales reads and writes linearly; "
      "Neo4j scales reads with causal clustering/read replicas, while scaling writes and very large graphs needs sharding via Fabric or composite databases.")]
S += [Paragraph("9. Operational Complexity", H2), tbl([["", "MongoDB", "Cassandra", "Neo4j"],
    ["Backup", "mongodump, snapshots, Ops/Cloud Manager", "nodetool snapshot, incremental backup per node", "neo4j-admin backup/dump (online backup is Enterprise)"],
    ["Monitoring", "mongostat, Atlas / Prometheus exporter", "nodetool, JMX, Prometheus; repair scheduling", "Metrics endpoint, query log, Bloom (Enterprise)"],
    ["Skills", "Moderate", "High (tuning, compaction, repair)", "Moderate (Cypher, graph modeling)"]], [60, 160, 160, 160])]
S += [Paragraph("10. Final Recommendation (per access pattern)", H2), tbl([["Access pattern", "Best choice", "Why"],
    ["Threat history by source", win[QN[0]] + " (measured)", "Single-partition / embedded array read keeps latency low."],
    ["Target and spread", win[QN[1]] + " (measured)", "Aggregation per source; Neo4j is best when traversing deeper relationships."],
    ["Daily volume analytics", win[QN[2]] + " (measured)", "Pre-partitioned by type and day (Cassandra) or indexed aggregation (MongoDB)."],
    ["Real-time insert throughput", win[QN[3]] + " (measured)", "Cassandra's log-structured write path scales best at large volumes."],
    ["False-positive community detection", "Neo4j", "SUSPICIOUS relationships and pattern matching are native; results are enriched from MongoDB."]],
    [140, 120, 280]),
    P("Overall: Cassandra (ingest and time-series), MongoDB (detail store and dashboards), Neo4j (relationship analysis for false positives).")]
doc.build(S)
print("DONE. See ./output/report.pdf and results.json", flush=True)

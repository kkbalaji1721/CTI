"""Seed the SAME fraud dataset into MongoDB, Cassandra and Neo4j (idempotent)."""
import random
from datetime import datetime, timedelta

from common.config import Config
from common import connections

USERS = [f"U{i}" for i in range(1, 9)]
MERCHANTS = ["Amazon", "Walmart", "Shell", "Uber", "Netflix", "Crypto-X", "GiftCardHub", "Starbucks"]
# money-transfer graph: U1->U2->U3->U1 is a fraud ring; U3->U4->U5 a chain; U6->U7 separate; U8 isolated
TRANSFERS = [("U1", "U2", 900), ("U2", "U3", 880), ("U3", "U1", 860),
             ("U3", "U4", 400), ("U4", "U5", 390), ("U6", "U7", 50)]


def build_transactions():
    rng = random.Random(42)
    base = datetime(2024, 6, 1, 9, 0, 0)
    txns = []
    for n in range(40):
        user = USERS[n % len(USERS)]
        txns.append({"txn_id": f"TXN-{1001 + n}", "user_id": user,
                     "amount": round(rng.uniform(5, 300), 2), "merchant": rng.choice(MERCHANTS[:5]),
                     "timestamp": base + timedelta(hours=7 * n), "risk_score": rng.randint(1, 40)})
    # make the fraud-ring members look suspicious
    for t in txns:
        if t["user_id"] in ("U1", "U2", "U3") and t["txn_id"] in ("TXN-1001", "TXN-1002", "TXN-1003", "TXN-1009"):
            t.update(amount=round(rng.uniform(800, 950), 2), merchant=rng.choice(MERCHANTS[5:7]),
                     risk_score=rng.randint(85, 98))
    return txns


def seed(cfg=None):
    cfg = cfg or Config.from_env()
    txns = build_transactions()

    # ---- MongoDB
    mc = connections.mongo_client(cfg)
    db = mc["fraud_db"]
    db.transactions.drop(); db.users.drop()
    db.transactions.insert_many([dict(t) for t in txns])
    db.transactions.create_index("txn_id", unique=True)
    db.users.insert_many([{"user_id": u, "name": f"User {u}", "account_age_days": 100 + 37 * i}
                          for i, u in enumerate(USERS)])
    mc.close()

    # ---- Cassandra
    cl = connections.cassandra_cluster(cfg)
    s = cl.connect()
    s.execute("CREATE KEYSPACE IF NOT EXISTS fraud_ks WITH replication = "
              "{'class': 'SimpleStrategy', 'replication_factor': 1}")
    s.set_keyspace("fraud_ks")
    s.execute("""CREATE TABLE IF NOT EXISTS user_profiles (
                   user_id text, event_time timestamp, txn_id text, amount double,
                   merchant text, risk_score int,
                   PRIMARY KEY ((user_id), event_time)
                 ) WITH CLUSTERING ORDER BY (event_time DESC)""")
    s.execute("TRUNCATE user_profiles")
    ins = s.prepare("INSERT INTO user_profiles (user_id, event_time, txn_id, amount, merchant, risk_score) "
                    "VALUES (?, ?, ?, ?, ?, ?)")
    for t in txns:
        s.execute(ins, (t["user_id"], t["timestamp"], t["txn_id"], t["amount"], t["merchant"], t["risk_score"]))
    cl.shutdown()

    # ---- Neo4j
    d = connections.neo4j_driver(cfg)
    with d.session() as ses:
        ses.run("MATCH (u:User) DETACH DELETE u")
        ses.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        ses.run("UNWIND $ids AS i CREATE (:User {id: i})", ids=USERS)
        for a, b, amt in TRANSFERS:
            ses.run("MATCH (a:User {id:$a}), (b:User {id:$b}) CREATE (a)-[:TRANSFERRED_TO {amount:$amt}]->(b)",
                    a=a, b=b, amt=amt)
    d.close()
    print(f"Seeded fraud dataset: {len(txns)} transactions, {len(USERS)} users, {len(TRANSFERS)} transfers")


if __name__ == "__main__":
    seed()

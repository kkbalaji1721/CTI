"""
Lab 16.2 - FraudQueryService (polyglot persistence)

  MongoDB    -> flexible document lookup          get_transaction(txn_id)
  Cassandra  -> time-ordered events per user      get_user_profile(user_id)
  Neo4j      -> multi-hop graph traversal         detect_fraud_rings(user_id, max_hops)

Features: connection pooling for all 3 drivers + a circuit breaker per backend
(3 consecutive failures -> backend marked unavailable, retried after 30 seconds).
"""
import logging
import time

from common.config import Config

log = logging.getLogger("fraud_service")


# --------------------------------------------------------------------------- circuit breaker
class CircuitOpenError(RuntimeError):
    """Raised when a backend is marked unavailable and the call is skipped."""


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half-open"

    def __init__(self, name, failure_threshold=3, reset_timeout=30.0, clock=time.monotonic):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._state = self.CLOSED
        self.consecutive_failures = 0
        self._opened_at = None

    @property
    def state(self):
        # after reset_timeout seconds an open breaker lets ONE trial call through
        if self._state == self.OPEN and self._clock() - self._opened_at >= self.reset_timeout:
            self._state = self.HALF_OPEN
        return self._state

    def call(self, fn, *args, **kwargs):
        if self.state == self.OPEN:
            raise CircuitOpenError(f"{self.name} is marked unavailable (circuit open)")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self):
        self.consecutive_failures = 0
        self._state = self.CLOSED

    def _on_failure(self):
        self.consecutive_failures += 1
        if self._state == self.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
            self._state = self.OPEN
            self._opened_at = self._clock()
            log.warning("circuit OPEN for %s after %d failures", self.name, self.consecutive_failures)


# --------------------------------------------------------------------------- the service
class FraudQueryService:
    MAX_POOL_SIZE = 10

    def __init__(self, config=None, mongo_db=None, cassandra_session=None,
                 neo4j_driver=None, clock=time.monotonic):
        """Creates the three connections. Pre-built clients can be injected (used by unit tests)."""
        cfg = config or Config.from_env()
        self._closers = []
        self.breakers = {n: CircuitBreaker(n, 3, 30.0, clock) for n in ("mongodb", "cassandra", "neo4j")}

        if mongo_db is None:                       # PyMongo: built-in pool, maxPoolSize=10
            from common.connections import mongo_client
            client = mongo_client(cfg, maxPoolSize=self.MAX_POOL_SIZE)
            mongo_db = client["fraud_db"]
            self._closers.append(client.close)
        self.mongo_db = mongo_db

        if cassandra_session is None:              # Cassandra: executor_threads sizes the request pool
            from common.connections import cassandra_cluster
            cluster = cassandra_cluster(cfg, executor_threads=self.MAX_POOL_SIZE)
            cassandra_session = cluster.connect("fraud_ks")
            self._closers.append(cluster.shutdown)
        self.cassandra = cassandra_session
        self._profile_stmt = self.cassandra.prepare(
            "SELECT user_id, event_time, txn_id, amount, merchant, risk_score "
            "FROM user_profiles WHERE user_id = ? ORDER BY event_time DESC LIMIT 10")

        if neo4j_driver is None:                   # Neo4j: max_connection_pool_size
            from common.connections import neo4j_driver as make_driver
            neo4j_driver = make_driver(cfg, max_connection_pool_size=self.MAX_POOL_SIZE)
            self._closers.append(neo4j_driver.close)
        self.neo4j = neo4j_driver

    # ---- MongoDB: flexible document lookup
    def get_transaction(self, txn_id):
        def q():
            return self.mongo_db.transactions.find_one({"txn_id": txn_id}, {"_id": 0})
        return self.breakers["mongodb"].call(q)

    # ---- Cassandra: time-ordered recent events (partition = user_id, clustering = event_time DESC)
    def get_user_profile(self, user_id):
        def q():
            rows = self.cassandra.execute(self._profile_stmt, (user_id,))
            return [r._asdict() for r in rows]
        events = self.breakers["cassandra"].call(q)
        return {"user_id": user_id, "recent_events": events, "event_count": len(events)}

    # ---- Neo4j: multi-hop traversal over the money-transfer graph
    def detect_fraud_rings(self, user_id, max_hops=3):
        if not isinstance(max_hops, int) or not 1 <= max_hops <= 5:
            raise ValueError("max_hops must be an integer between 1 and 5")
        # Cypher cannot parameterise the hop range, so it is validated above and formatted in
        cypher = (f"MATCH path = (u:User {{id: $uid}})-[:TRANSFERRED_TO*1..{max_hops}]-(connected:User) "
                  "RETURN [n IN nodes(path) | n.id] AS ids, length(path) AS hops LIMIT 50")

        def q():
            with self.neo4j.session() as s:
                return [{"ids": r["ids"], "hops": r["hops"]} for r in s.run(cypher, uid=user_id)]
        paths = self.breakers["neo4j"].call(q)
        connected = sorted({i for p in paths for i in p["ids"]} - {user_id})
        ring = any(len(p["ids"]) > 2 and p["ids"][0] == p["ids"][-1] for p in paths)
        return {"user_id": user_id, "max_hops": max_hops, "paths": paths,
                "connected_users": connected, "ring_detected": ring}

    # ---- merged result: full fraud analysis workflow
    def analyze(self, user_id, txn_id=None, max_hops=3):
        """Query all three backends and merge. A failing/open backend degrades the result, not the call."""
        result = {"user_id": user_id, "transaction": None, "profile": None, "graph": None,
                  "degraded_backends": [], "risk_level": "LOW"}
        steps = [("transaction", "mongodb", lambda: self.get_transaction(txn_id) if txn_id else None),
                 ("profile", "cassandra", lambda: self.get_user_profile(user_id)),
                 ("graph", "neo4j", lambda: self.detect_fraud_rings(user_id, max_hops))]
        for key, backend, fn in steps:
            try:
                result[key] = fn()
            except Exception as exc:  # CircuitOpenError or a driver error
                log.warning("%s unavailable: %s", backend, exc)
                result["degraded_backends"].append(backend)

        txn, graph, profile = result["transaction"], result["graph"], result["profile"]
        score = 0
        if txn and txn.get("risk_score", 0) >= 80:
            score += 2
        if graph and graph["ring_detected"]:
            score += 2
        elif graph and len(graph["connected_users"]) >= 3:
            score += 1
        if profile and any(e["risk_score"] >= 80 for e in profile["recent_events"]):
            score += 1
        result["risk_level"] = "HIGH" if score >= 3 else "MEDIUM" if score >= 1 else "LOW"
        return result

    def close(self):
        for c in self._closers:
            try:
                c()
            except Exception:  # noqa
                pass

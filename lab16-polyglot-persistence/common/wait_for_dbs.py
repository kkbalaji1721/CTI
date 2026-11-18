"""Block until MongoDB, Cassandra and Neo4j accept connections (Cassandra can take ~1-2 min)."""
import sys
import time

from common.config import Config
from common import connections


def _try(name, fn, timeout):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            fn()
            print(f"  [ok] {name} is ready")
            return True
        except Exception as exc:  # noqa
            last = exc
            time.sleep(5)
    print(f"  [FAIL] {name} not ready: {last}")
    return False


def wait_for_all(cfg: Config = None, timeout=300):
    cfg = cfg or Config.from_env()
    print("Waiting for databases ...")

    def mongo():
        c = connections.mongo_client(cfg)
        c.admin.command("ping")
        c.close()

    def cassandra():
        cl = connections.cassandra_cluster(cfg)
        s = cl.connect()
        s.execute("SELECT release_version FROM system.local")
        cl.shutdown()

    def neo4j():
        d = connections.neo4j_driver(cfg)
        d.verify_connectivity()
        d.close()

    return all([_try("MongoDB", mongo, timeout),
                _try("Cassandra", cassandra, timeout),
                _try("Neo4j", neo4j, timeout)])


if __name__ == "__main__":
    sys.exit(0 if wait_for_all() else 1)

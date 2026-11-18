import os
from dataclasses import dataclass, field


@dataclass
class Config:
    mongo_uri: str = "mongodb://localhost:27017"
    cassandra_hosts: list = field(default_factory=lambda: ["localhost"])
    cassandra_port: int = 9042
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    @classmethod
    def from_env(cls):
        return cls(
            mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
            cassandra_hosts=os.getenv("CASSANDRA_HOSTS", "localhost").split(","),
            cassandra_port=int(os.getenv("CASSANDRA_PORT", "9042")),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "password123"),
        )

"""Helpers that open real connections (drivers imported lazily so unit tests need no drivers)."""
from common.config import Config


def mongo_client(cfg: Config, **kw):
    from pymongo import MongoClient
    return MongoClient(cfg.mongo_uri, serverSelectionTimeoutMS=3000, **kw)


def cassandra_cluster(cfg: Config, **kw):
    from cassandra.cluster import Cluster
    return Cluster(cfg.cassandra_hosts, port=cfg.cassandra_port, **kw)


def neo4j_driver(cfg: Config, **kw):
    from neo4j import GraphDatabase
    return GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password), **kw)

"""Unit tests - every database driver is mocked, so no database is needed."""
import unittest
from collections import namedtuple
from unittest import mock

from lab16_2.fraud_service import CircuitBreaker, CircuitOpenError, FraudQueryService

Row = namedtuple("Row", "user_id event_time txn_id amount merchant risk_score")


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make_service(clock=None):
    mongo_db, cass, neo = mock.MagicMock(), mock.MagicMock(), mock.MagicMock()
    mongo_db.transactions.find_one.return_value = {
        "txn_id": "TXN-1", "user_id": "U1", "amount": 900.0, "merchant": "Crypto-X", "risk_score": 95}
    cass.execute.return_value = [Row("U1", "2024-06-15", "TXN-1", 900.0, "Crypto-X", 95),
                                 Row("U1", "2024-06-14", "TXN-0", 20.0, "Uber", 10)]
    session = neo.session.return_value.__enter__.return_value
    session.run.return_value = [{"ids": ["U1", "U2"], "hops": 1},
                                {"ids": ["U1", "U2", "U3", "U1"], "hops": 3}]
    svc = FraudQueryService(mongo_db=mongo_db, cassandra_session=cass, neo4j_driver=neo,
                            clock=clock or FakeClock())
    return svc, mongo_db, cass, neo


class TestBackendMethods(unittest.TestCase):
    def test_get_transaction_uses_mongodb(self):
        svc, mongo, _, _ = make_service()
        txn = svc.get_transaction("TXN-1")
        mongo.transactions.find_one.assert_called_once_with({"txn_id": "TXN-1"}, {"_id": 0})
        self.assertEqual(txn["merchant"], "Crypto-X")

    def test_get_user_profile_uses_cassandra(self):
        svc, _, cass, _ = make_service()
        prof = svc.get_user_profile("U1")
        self.assertEqual(prof["event_count"], 2)
        self.assertEqual(prof["recent_events"][0]["txn_id"], "TXN-1")
        sql = cass.prepare.call_args[0][0]
        self.assertIn("ORDER BY event_time DESC LIMIT 10", sql)

    def test_detect_fraud_rings_uses_neo4j(self):
        svc, _, _, neo = make_service()
        res = svc.detect_fraud_rings("U1", max_hops=3)
        cypher = neo.session.return_value.__enter__.return_value.run.call_args[0][0]
        self.assertIn("TRANSFERRED_TO*1..3", cypher)
        self.assertEqual(res["connected_users"], ["U2", "U3"])
        self.assertTrue(res["ring_detected"])

    def test_max_hops_is_validated(self):
        svc, *_ = make_service()
        for bad in (0, 6, "3; DROP", None):
            with self.assertRaises(ValueError):
                svc.detect_fraud_rings("U1", max_hops=bad)


class TestMergedResults(unittest.TestCase):
    def test_analyze_merges_three_backends(self):
        svc, *_ = make_service()
        res = svc.analyze("U1", "TXN-1")
        self.assertEqual(res["transaction"]["txn_id"], "TXN-1")
        self.assertEqual(res["profile"]["event_count"], 2)
        self.assertTrue(res["graph"]["ring_detected"])
        self.assertEqual(res["degraded_backends"], [])
        self.assertEqual(res["risk_level"], "HIGH")

    def test_analyze_degrades_gracefully_when_backend_fails(self):
        svc, mongo, *_ = make_service()
        mongo.transactions.find_one.side_effect = ConnectionError("mongo down")
        res = svc.analyze("U1", "TXN-1")
        self.assertIsNone(res["transaction"])
        self.assertEqual(res["degraded_backends"], ["mongodb"])
        self.assertIsNotNone(res["graph"])          # other backends still answered


class TestCircuitBreaker(unittest.TestCase):
    def test_opens_after_three_consecutive_failures_and_skips_calls(self):
        svc, mongo, *_ = make_service()
        mongo.transactions.find_one.side_effect = ConnectionError("down")
        for _ in range(3):
            with self.assertRaises(ConnectionError):
                svc.get_transaction("TXN-1")
        self.assertEqual(svc.breakers["mongodb"].state, CircuitBreaker.OPEN)
        calls = mongo.transactions.find_one.call_count
        with self.assertRaises(CircuitOpenError):
            svc.get_transaction("TXN-1")
        self.assertEqual(mongo.transactions.find_one.call_count, calls)  # backend NOT called

    def test_success_resets_failure_counter(self):
        svc, mongo, *_ = make_service()
        good = mongo.transactions.find_one.return_value
        mongo.transactions.find_one.side_effect = [ConnectionError(), ConnectionError(), good, ConnectionError()]
        for expect_error in (True, True, False, True):
            if expect_error:
                with self.assertRaises(ConnectionError):
                    svc.get_transaction("T")
            else:
                svc.get_transaction("T")
        self.assertEqual(svc.breakers["mongodb"].state, CircuitBreaker.CLOSED)   # never 3 in a row

    def test_retries_after_30_seconds(self):
        clock = FakeClock()
        svc, mongo, *_ = make_service(clock)
        good = mongo.transactions.find_one.return_value
        mongo.transactions.find_one.side_effect = ConnectionError()
        for _ in range(3):
            with self.assertRaises(ConnectionError):
                svc.get_transaction("T")
        clock.t = 29
        with self.assertRaises(CircuitOpenError):
            svc.get_transaction("T")
        clock.t = 31                                  # 30s passed -> half-open trial call allowed
        mongo.transactions.find_one.side_effect = None
        mongo.transactions.find_one.return_value = good
        self.assertEqual(svc.get_transaction("T")["txn_id"], "TXN-1")
        self.assertEqual(svc.breakers["mongodb"].state, CircuitBreaker.CLOSED)

    def test_failed_trial_reopens_circuit(self):
        clock = FakeClock()
        svc, mongo, *_ = make_service(clock)
        mongo.transactions.find_one.side_effect = ConnectionError()
        for _ in range(3):
            with self.assertRaises(ConnectionError):
                svc.get_transaction("T")
        clock.t = 31
        with self.assertRaises(ConnectionError):      # trial call fails
            svc.get_transaction("T")
        with self.assertRaises(CircuitOpenError):     # open again immediately
            svc.get_transaction("T")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Integration test - needs the 3 real databases (docker compose). Auto-skipped otherwise."""
import json
import os
import unittest

from lab16_2.fraud_service import FraudQueryService


@unittest.skipUnless(os.getenv("RUN_INTEGRATION") == "1", "set RUN_INTEGRATION=1 with databases running")
class TestFullFraudWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lab16_2.seed_data import seed
        seed()
        cls.svc = FraudQueryService()

    @classmethod
    def tearDownClass(cls):
        cls.svc.close()

    def test_each_backend(self):
        txn = self.svc.get_transaction("TXN-1001")
        self.assertEqual(txn["user_id"], "U1")
        prof = self.svc.get_user_profile("U1")
        times = [e["event_time"] for e in prof["recent_events"]]
        self.assertEqual(times, sorted(times, reverse=True))          # Cassandra: newest first
        g1 = self.svc.detect_fraud_rings("U1", max_hops=1)
        self.assertEqual(g1["connected_users"], ["U2", "U3"])          # 1 hop (undirected)

    def test_full_analysis_flags_fraud_ring(self):
        res = self.svc.analyze("U1", "TXN-1001", max_hops=3)
        print("\n--- merged analysis for U1 ---")
        print(json.dumps(res, indent=2, default=str)[:1800])
        self.assertTrue(res["graph"]["ring_detected"])
        self.assertEqual(res["risk_level"], "HIGH")
        self.assertEqual(res["degraded_backends"], [])

    def test_clean_user_is_low_risk(self):
        res = self.svc.analyze("U8", None, max_hops=3)                  # U8 is isolated
        self.assertFalse(res["graph"]["ring_detected"])
        self.assertEqual(res["graph"]["connected_users"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

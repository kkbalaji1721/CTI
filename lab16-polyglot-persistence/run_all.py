"""Runs EVERY lab task in order and saves the console output to output/lab_output.txt."""
import os
import sys
import unittest

from common.wait_for_dbs import wait_for_all


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


def banner(text):
    print("\n" + "#" * 78 + f"\n# {text}\n" + "#" * 78)


def run_tests(module, title):
    banner(title)
    suite = unittest.defaultTestLoader.loadTestsFromName(module)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    return result.wasSuccessful()


def main():
    os.makedirs("output", exist_ok=True)
    log = open("output/lab_output.txt", "w")
    sys.stdout = Tee(sys.__stdout__, log)
    ok = True
    try:
        banner("STEP 0: waiting for MongoDB, Cassandra and Neo4j")
        if not wait_for_all():
            print("Databases not reachable - start them with: docker compose up")
            return 1

        from lab16_1 import run_lab16_1, activity_16_1_hybrid
        from lab16_2 import seed_data, benchmark

        banner("LAB 16.1: model the same dataset in three databases")
        run_lab16_1.main()
        banner("ACTIVITY 16.1: hybrid architecture")
        activity_16_1_hybrid.main()

        banner("LAB 16.2: seed fraud dataset into the 3 databases")
        seed_data.seed()
        ok &= run_tests("lab16_2.tests.test_unit", "LAB 16.2: UNIT TESTS (mocked drivers)")
        os.environ["RUN_INTEGRATION"] = "1"
        ok &= run_tests("lab16_2.tests.test_integration", "LAB 16.2: INTEGRATION TEST (real databases)")
        banner("LAB 16.2: LATENCY MEASUREMENTS")
        benchmark.main()

        banner("ALL DONE - " + ("ALL TESTS PASSED" if ok else "SOME TESTS FAILED"))
        print("Results saved in output/lab_output.txt and output/latency_report.md")
    finally:
        sys.stdout = sys.__stdout__
        log.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Command dispatcher for the Lab 9 image.

  lab setup          initiate the replica set (idempotent)
  lab lab01          Lab 9.1  write-concern latency (+ j:true/j:false activity)
  lab lab02          Lab 9.2  network-partition simulation
  lab all            setup + lab01 + lab02
  lab status         show replica-set member states
  lab report ...     build the PDF report from the saved results
  lab print-compose  print the docker-compose.yml baked into this image
"""
import sys

HELP = __doc__


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    rest = sys.argv[2:]
    if cmd == "setup":
        import setup_replicaset; setup_replicaset.main()
    elif cmd in ("lab01", "9.1"):
        import lab_01_write_concern_latency as m; m.main()
    elif cmd in ("lab02", "9.2"):
        import lab_02_simulate_partition as m; m.main()
    elif cmd == "all":
        import setup_replicaset, lab_01_write_concern_latency as a, lab_02_simulate_partition as b
        setup_replicaset.main(); a.main(); b.main()
    elif cmd == "status":
        from pymongo import MongoClient
        from common import RS_URI, replica_set_members
        c = MongoClient(RS_URI, serverSelectionTimeoutMS=5000)
        for mem in replica_set_members(c):
            print(f"  {mem['name']:<14} {mem['state']:<10} health={mem['health']}")
    elif cmd == "report":
        import make_report; make_report.main(rest)
    elif cmd == "print-compose":
        print(open("/lab/docker-compose.yml", encoding="utf-8").read())
    else:
        print(HELP)


if __name__ == "__main__":
    main()

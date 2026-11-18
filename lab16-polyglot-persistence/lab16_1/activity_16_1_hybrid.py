"""
Activity 16.1 - Hybrid architecture
  MongoDB   : operational data (students, enrollments)
  Cassandra : append-only audit log of every enrollment decision (time series)
  Neo4j     : prerequisite chain queries (CS101 -> CS201 -> DB301 -> ML401)
Requires lab16_1/run_lab16_1.py to have loaded the Course graph first.
"""
from datetime import datetime

from common.config import Config
from common import connections


class HybridEnrollment:
    def __init__(self, cfg=None):
        cfg = cfg or Config.from_env()
        self.mc = connections.mongo_client(cfg)
        self.mongo = self.mc["university_ops"]
        self.cl = connections.cassandra_cluster(cfg)
        self.cass = self.cl.connect()
        self.cass.execute("CREATE KEYSPACE IF NOT EXISTS university WITH replication = "
                          "{'class':'SimpleStrategy','replication_factor':1}")
        self.cass.set_keyspace("university")
        self.cass.execute("""CREATE TABLE IF NOT EXISTS enrollment_audit (
            student_id text, event_time timestamp, course_id text, action text, detail text,
            PRIMARY KEY ((student_id), event_time)) WITH CLUSTERING ORDER BY (event_time DESC)""")
        self.cass.execute("TRUNCATE enrollment_audit")
        self.audit_stmt = self.cass.prepare(
            "INSERT INTO enrollment_audit (student_id, event_time, course_id, action, detail) VALUES (?,?,?,?,?)")
        self.neo = connections.neo4j_driver(cfg)

    def reset(self):
        self.mongo.students.drop()
        self.mongo.students.insert_many([
            {"_id": "S1", "name": "Alice", "completed": ["CS101", "CS201"], "enrolled": []},
            {"_id": "S3", "name": "Carol", "completed": ["CS101", "CS201", "DB301"], "enrolled": []},
            {"_id": "S4", "name": "Dave", "completed": ["CS101"], "enrolled": []}])

    def prerequisites(self, course_id):
        """Neo4j: every course that must be finished (directly or transitively) before course_id."""
        with self.neo.session() as s:
            return sorted(r["id"] for r in s.run(
                "MATCH (p:Course)-[:PREREQUISITE_OF*]->(:Course {id:$c}) RETURN DISTINCT p.id AS id", c=course_id))

    def chain(self, start, end):
        with self.neo.session() as s:
            r = s.run("MATCH path = (a:Course {id:$a})-[:PREREQUISITE_OF*]->(b:Course {id:$b}) "
                      "RETURN [n IN nodes(path) | n.title] AS titles", a=start, b=end).single()
            return r["titles"] if r else []

    def enroll(self, student_id, course_id):
        student = self.mongo.students.find_one({"_id": student_id})
        missing = sorted(set(self.prerequisites(course_id)) - set(student["completed"]))
        if missing:
            action, detail = "DENIED", f"missing prerequisites: {', '.join(missing)}"
        else:
            self.mongo.students.update_one({"_id": student_id}, {"$addToSet": {"enrolled": course_id}})
            action, detail = "ENROLLED", "all prerequisites satisfied"
        self.cass.execute(self.audit_stmt, (student_id, datetime.utcnow(), course_id, action, detail))
        print(f"  {student['name']:<6} -> {course_id}: {action} ({detail})")
        return action

    def audit_log(self, student_id):
        return [(r.course_id, r.action, r.detail) for r in self.cass.execute(
            "SELECT course_id, action, detail FROM enrollment_audit WHERE student_id = %s", (student_id,))]

    def close(self):
        self.mc.close(); self.cl.shutdown(); self.neo.close()


def main():
    print("\n" + "=" * 78)
    print("ACTIVITY 16.1 - Hybrid architecture (MongoDB + Cassandra + Neo4j)")
    print("=" * 78)
    h = HybridEnrollment()
    h.reset()
    print("Neo4j prerequisite chain CS101 -> ML401:", " -> ".join(h.chain("CS101", "ML401")))
    print("Neo4j: prerequisites of ML401 =", h.prerequisites("ML401"))
    print("Enrollment requests (operational data in MongoDB, decisions logged to Cassandra):")
    h.enroll("S1", "DB301")   # Alice has CS101+CS201            -> ENROLLED
    h.enroll("S4", "DB301")   # Dave only has CS101              -> DENIED
    h.enroll("S3", "ML401")   # Carol has CS101+CS201+DB301      -> ENROLLED
    print("Cassandra audit log for Dave:", h.audit_log("S4"))
    print("MongoDB enrolled:", {s["name"]: s["enrolled"] for s in h.mongo.students.find()})
    h.close()


if __name__ == "__main__":
    main()

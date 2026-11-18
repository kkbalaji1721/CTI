"""Lab 16.1 - same university enrollment dataset modelled in MongoDB, Cassandra and Neo4j."""
import time

from common.config import Config
from common import connections

STUDENTS = {"S1": "Alice", "S2": "Bob", "S3": "Carol", "S4": "Dave"}
COURSES = {"CS101": "Intro to Programming", "CS201": "Data Structures",
           "DB301": "Databases", "ML401": "Machine Learning"}
ENROLL = {"S1": ["CS101", "CS201", "DB301"], "S2": ["CS101", "DB301"],
          "S3": ["CS201", "ML401"], "S4": ["CS101", "ML401"]}
PREREQ = [("CS101", "CS201"), ("CS201", "DB301"), ("DB301", "ML401")]
TARGET_STUDENT, TARGET_NAME, TARGET_COURSE = "S1", "Alice", "CS101"


def timed(fn):
    t = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t) * 1000


# ----------------------------------------------------------------------------- MongoDB
def mongo_part(cfg):
    c = connections.mongo_client(cfg)
    db = c["university"]
    db.students.drop(); db.courses.drop()
    db.students.insert_many([{"_id": s, "name": n, "course_ids": ENROLL[s]} for s, n in STUDENTS.items()])
    db.courses.insert_many([{"_id": cid, "title": t,
                             "roster": [{"id": s, "name": STUDENTS[s]} for s in STUDENTS if cid in ENROLL[s]]}
                            for cid, t in COURSES.items()])

    def q1():
        return db.students.find_one({"name": TARGET_NAME})["course_ids"]

    def q2():
        return [r["name"] for r in db.courses.find_one({"_id": TARGET_COURSE})["roster"]]

    def q3():
        mine = db.students.find_one({"name": TARGET_NAME})["course_ids"]
        return sorted(db.students.distinct("name", {"name": {"$ne": TARGET_NAME}, "course_ids": {"$in": mine}}))
    res = {k: timed(f) for k, f in (("q1", q1), ("q2", q2), ("q3", q3))}
    c.close()
    return res


# ----------------------------------------------------------------------------- Cassandra
def cassandra_part(cfg):
    cl = connections.cassandra_cluster(cfg)
    s = cl.connect()
    s.execute("CREATE KEYSPACE IF NOT EXISTS university WITH replication = "
              "{'class':'SimpleStrategy','replication_factor':1}")
    s.set_keyspace("university")
    s.execute("""CREATE TABLE IF NOT EXISTS student_courses (student_id text, course_id text,
                 student_name text, course_title text, PRIMARY KEY ((student_id), course_id))""")
    s.execute("""CREATE TABLE IF NOT EXISTS course_students (course_id text, student_id text,
                 student_name text, course_title text, PRIMARY KEY ((course_id), student_id))""")
    s.execute("TRUNCATE student_courses"); s.execute("TRUNCATE course_students")
    i1 = s.prepare("INSERT INTO student_courses (student_id, course_id, student_name, course_title) VALUES (?,?,?,?)")
    i2 = s.prepare("INSERT INTO course_students (course_id, student_id, student_name, course_title) VALUES (?,?,?,?)")
    for sid, cids in ENROLL.items():                       # denormalised: write each fact to both tables
        for cid in cids:
            s.execute(i1, (sid, cid, STUDENTS[sid], COURSES[cid]))
            s.execute(i2, (cid, sid, STUDENTS[sid], COURSES[cid]))
    q1s = s.prepare("SELECT course_id FROM student_courses WHERE student_id = ?")
    q2s = s.prepare("SELECT student_name FROM course_students WHERE course_id = ?")

    def q1():
        return sorted(r.course_id for r in s.execute(q1s, (TARGET_STUDENT,)))

    def q2():
        return sorted(r.student_name for r in s.execute(q2s, (TARGET_COURSE,)))

    def q3():                                              # no JOIN: combine two queries in the app
        names = set()
        for cid in q1():
            names.update(r.student_name for r in s.execute(q2s, (cid,)))
        return sorted(names - {TARGET_NAME})
    res = {k: timed(f) for k, f in (("q1", q1), ("q2", q2), ("q3", q3))}
    cl.shutdown()
    return res


# ----------------------------------------------------------------------------- Neo4j
def neo4j_part(cfg):
    d = connections.neo4j_driver(cfg)
    with d.session() as ses:
        ses.run("MATCH (n) WHERE n:Student OR n:Course DETACH DELETE n")
        for sid, n in STUDENTS.items():
            ses.run("CREATE (:Student {id:$i, name:$n})", i=sid, n=n)
        for cid, t in COURSES.items():
            ses.run("CREATE (:Course {id:$i, title:$t})", i=cid, t=t)
        for sid, cids in ENROLL.items():
            for cid in cids:
                ses.run("MATCH (s:Student {id:$s}), (c:Course {id:$c}) CREATE (s)-[:ENROLLED_IN]->(c)", s=sid, c=cid)
        for a, b in PREREQ:
            ses.run("MATCH (a:Course {id:$a}), (b:Course {id:$b}) CREATE (a)-[:PREREQUISITE_OF]->(b)", a=a, b=b)

        def q1():
            return sorted(r["id"] for r in ses.run(
                "MATCH (:Student {name:$n})-[:ENROLLED_IN]->(c:Course) RETURN c.id AS id", n=TARGET_NAME))

        def q2():
            return sorted(r["name"] for r in ses.run(
                "MATCH (s:Student)-[:ENROLLED_IN]->(:Course {id:$c}) RETURN s.name AS name", c=TARGET_COURSE))

        def q3():
            return sorted(r["name"] for r in ses.run(
                "MATCH (s1:Student)-[:ENROLLED_IN]->(c:Course)<-[:ENROLLED_IN]-(s2:Student) "
                "WHERE s1.name = $n AND s2.name <> $n RETURN DISTINCT s2.name AS name", n=TARGET_NAME))
        res = {k: timed(f) for k, f in (("q1", q1), ("q2", q2), ("q3", q3))}
    d.close()
    return res


def main(cfg=None):
    cfg = cfg or Config.from_env()
    print("=" * 78)
    print("LAB 16.1 - Model the same dataset in MongoDB, Cassandra and Neo4j")
    print("=" * 78)
    results = {"MongoDB": mongo_part(cfg), "Cassandra": cassandra_part(cfg), "Neo4j": neo4j_part(cfg)}
    labels = {"q1": f"Q1 courses of {TARGET_NAME}", "q2": f"Q2 students in {TARGET_COURSE}",
              "q3": f"Q3 students sharing a course with {TARGET_NAME}"}
    for q in ("q1", "q2", "q3"):
        print(f"\n{labels[q]}")
        for db, r in results.items():
            out, ms = r[q]
            print(f"  {db:<10} -> {out}   ({ms:.2f} ms)")
    print("\nSyntax / performance comparison: see lab16_1/COMPARISON.md")
    return results


if __name__ == "__main__":
    main()

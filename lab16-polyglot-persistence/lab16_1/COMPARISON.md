# Lab 16.1 - Schema design and comparison

## 1. Schema designs
| | MongoDB (document) | Cassandra (query-driven) | Neo4j (graph) |
|---|---|---|---|
| Structure | `students` {name, course_ids[]} and `courses` {title, roster[]} | `student_courses` PK `((student_id), course_id)` and `course_students` PK `((course_id), student_id)` | `(:Student)-[:ENROLLED_IN]->(:Course)`, plus `(:Course)-[:PREREQUISITE_OF]->(:Course)` |
| Design driver | Embed what is read together | One table per query, data duplicated | Relationships are first-class and stored as pointers |
| Duplicated data | Yes (roster and course_ids) | Yes (every enrollment stored twice) | No |

## 2. Equivalent queries
| Query | MongoDB | Cassandra | Neo4j |
|---|---|---|---|
| Courses of a student | `db.students.findOne({name:'Alice'})` | `SELECT course_id FROM student_courses WHERE student_id='S1'` | `MATCH (:Student {name:'Alice'})-[:ENROLLED_IN]->(c) RETURN c` |
| Students in a course | `db.courses.findOne({_id:'CS101'})` | `SELECT student_name FROM course_students WHERE course_id='CS101'` | `MATCH (s)-[:ENROLLED_IN]->(:Course {id:'CS101'}) RETURN s` |
| Students sharing a course | 2 steps: read Alice's course_ids, then `distinct("name", {course_ids: {$in: ids}})` | Application-side join: Q1, then Q2 for every course, merge results | One pattern: `(s1)-[:ENROLLED_IN]->(c)<-[:ENROLLED_IN]-(s2)` |

## 3. Syntax complexity and expected performance
| | MongoDB | Cassandra | Neo4j |
|---|---|---|---|
| Simple lookups (Q1, Q2) | Very simple, single read by key | Very simple, single-partition read, very predictable | Simple, one hop |
| Shared-course query (Q3) | Medium (two steps or `$lookup` aggregation) | Hardest (no joins, manual combination in code, N+1 reads) | Easiest and most readable (one MATCH) |
| Performance profile | Fast indexed reads, cost grows with large embedded arrays | Fastest and most predictable at huge scale for known queries, linear horizontal scaling | Traversal cost depends on neighbours visited, not total data size; slower for bulk scans/aggregations |
| Weakness | Many-to-many needs duplication or `$lookup` | Every new query = new table; ad-hoc queries are impossible | Harder to shard/scale writes horizontally |

**Conclusion:** the right choice depends on the access pattern. Key-based document reads suit MongoDB, high-volume time-ordered/known-query workloads suit Cassandra, and relationship-heavy questions (shared courses, prerequisite chains) suit Neo4j. That is why Activity 16.1 combines all three (polyglot persistence).

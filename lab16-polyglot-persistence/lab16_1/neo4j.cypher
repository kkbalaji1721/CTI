// Lab 16.1 - Neo4j graph model.   Run: cypher-shell -u neo4j -p password123 -f lab16_1/neo4j.cypher
MATCH (n) WHERE n:Student OR n:Course DETACH DELETE n;
CREATE (a:Student {id:'S1', name:'Alice'}), (b:Student {id:'S2', name:'Bob'}),
       (c:Student {id:'S3', name:'Carol'}), (d:Student {id:'S4', name:'Dave'}),
       (cs1:Course {id:'CS101', title:'Intro to Programming'}), (cs2:Course {id:'CS201', title:'Data Structures'}),
       (db:Course {id:'DB301', title:'Databases'}), (ml:Course {id:'ML401', title:'Machine Learning'}),
       (a)-[:ENROLLED_IN]->(cs1), (a)-[:ENROLLED_IN]->(cs2), (a)-[:ENROLLED_IN]->(db),
       (b)-[:ENROLLED_IN]->(cs1), (b)-[:ENROLLED_IN]->(db),
       (c)-[:ENROLLED_IN]->(cs2), (c)-[:ENROLLED_IN]->(ml),
       (d)-[:ENROLLED_IN]->(cs1), (d)-[:ENROLLED_IN]->(ml),
       (cs1)-[:PREREQUISITE_OF]->(cs2), (cs2)-[:PREREQUISITE_OF]->(db), (db)-[:PREREQUISITE_OF]->(ml);

// Q1: all courses for a student
MATCH (:Student {name:'Alice'})-[:ENROLLED_IN]->(c:Course) RETURN c.id, c.title;
// Q2: all students in a course
MATCH (s:Student)-[:ENROLLED_IN]->(:Course {id:'CS101'}) RETURN s.name;
// Q3: students who share a course with Alice
MATCH (s1:Student)-[:ENROLLED_IN]->(c:Course)<-[:ENROLLED_IN]-(s2:Student)
WHERE s1.name = 'Alice' AND s2.name <> 'Alice' RETURN DISTINCT s2.name;

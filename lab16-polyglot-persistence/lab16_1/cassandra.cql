-- Lab 16.1 - Cassandra query-driven design.   Run: cqlsh -f lab16_1/cassandra.cql
CREATE KEYSPACE IF NOT EXISTS university WITH replication = {'class':'SimpleStrategy','replication_factor':1};
USE university;

-- one table per query: partition key = the thing we filter on
CREATE TABLE IF NOT EXISTS student_courses (
  student_id text, course_id text, student_name text, course_title text,
  PRIMARY KEY ((student_id), course_id));
CREATE TABLE IF NOT EXISTS course_students (
  course_id text, student_id text, student_name text, course_title text,
  PRIMARY KEY ((course_id), student_id));

INSERT INTO student_courses (student_id, course_id, student_name, course_title) VALUES ('S1','CS101','Alice','Intro to Programming');
INSERT INTO course_students (course_id, student_id, student_name, course_title) VALUES ('CS101','S1','Alice','Intro to Programming');
-- (the Python runner loads the full data set into both tables)

-- Q1: SELECT course_id, course_title FROM student_courses WHERE student_id = 'S1';
-- Q2: SELECT student_id, student_name FROM course_students WHERE course_id = 'CS101';
-- Q3: no join in CQL -> Q1 for Alice, then Q2 for each of her courses, de-duplicate in the application.

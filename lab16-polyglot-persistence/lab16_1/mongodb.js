// Lab 16.1 - MongoDB document model.   Run: mongosh < lab16_1/mongodb.js
use university;
db.students.drop(); db.courses.drop();

// Students embed the ids of their courses  -> "courses of a student" is ONE read
db.students.insertMany([
  { _id: "S1", name: "Alice", course_ids: ["CS101", "CS201", "DB301"] },
  { _id: "S2", name: "Bob",   course_ids: ["CS101", "DB301"] },
  { _id: "S3", name: "Carol", course_ids: ["CS201", "ML401"] },
  { _id: "S4", name: "Dave",  course_ids: ["CS101", "ML401"] }
]);
// Courses embed a student roster          -> "students in a course" is ONE read
db.courses.insertMany([
  { _id: "CS101", title: "Intro to Programming", roster: [{id:"S1",name:"Alice"},{id:"S2",name:"Bob"},{id:"S4",name:"Dave"}] },
  { _id: "CS201", title: "Data Structures",      roster: [{id:"S1",name:"Alice"},{id:"S3",name:"Carol"}] },
  { _id: "DB301", title: "Databases",            roster: [{id:"S1",name:"Alice"},{id:"S2",name:"Bob"}] },
  { _id: "ML401", title: "Machine Learning",     roster: [{id:"S3",name:"Carol"},{id:"S4",name:"Dave"}] }
]);

// Q1: all courses for a student
db.students.findOne({ name: "Alice" }, { course_ids: 1, _id: 0 });
// Q2: all students in a course
db.courses.findOne({ _id: "CS101" }, { roster: 1, _id: 0 });
// Q3: students who share a course with Alice
var alice = db.students.findOne({ name: "Alice" });
db.students.distinct("name", { name: { $ne: "Alice" }, course_ids: { $in: alice.course_ids } });

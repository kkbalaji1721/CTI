// Lab 8.1 "Try it yourself" - mongosh file: replica set WITH AN ARBITER.
// Members: mongo-rs0-1 (data) + mongo-rs0-2 (data) + mongo-arbiter (votes only).
//     mongosh --port 27017 --file lab_8_1_arbiter.js

print("=== rs.initiate() with an arbiter ===");
try {
  printjson(rs.initiate({
    _id: "rs0",
    members: [
      { _id: 0, host: "mongo-rs0-1:27017" },
      { _id: 1, host: "mongo-rs0-2:27017" },
      { _id: 2, host: "mongo-arbiter:27017", arbiterOnly: true }
    ]
  }));
} catch (e) {
  print("rs.initiate skipped: " + e.message);
}

print("\nWaiting for an election to finish...");
let primary = null;
for (let i = 0; i < 60 && !primary; i++) {
  try { primary = rs.status().members.find(m => m.stateStr === "PRIMARY"); } catch (e) {}
  if (!primary) sleep(1000);
}
print(primary ? "PRIMARY elected: " + primary.name : "No primary yet!");

print("\n=== rs.status() summary ===");
rs.status().members.forEach(m => {
  print(m.name.padEnd(30) + m.stateStr.padEnd(12) + "health=" + m.health);
});

print("\n=== rs.conf(): who votes, who stores data? ===");
let voters = 0, dataNodes = 0;
rs.conf().members.forEach(m => {
  const holdsData = !m.arbiterOnly;
  voters += m.votes;
  if (holdsData) dataNodes++;
  print(m.host.padEnd(30) + "votes=" + m.votes + "  arbiterOnly=" + m.arbiterOnly +
        "  storesData=" + holdsData);
});
print("\nVoting members : " + voters + "   (majority needed to elect = " +
      (Math.floor(voters / 2) + 1) + ")");
print("Data-bearing   : " + dataNodes);

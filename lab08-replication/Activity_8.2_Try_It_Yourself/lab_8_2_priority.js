// Lab 8.2 "Try it yourself" - mongosh file: priorities + stepDown.
// The Python script runs this file against the current PRIMARY in two phases,
// selected by a PHASE_ARG variable that Python prepends to the script:
//     PHASE=reconfig  -> give each member a different priority
//     PHASE=stepdown  -> rs.stepDown(20) and watch who wins the election
//     (anything else) -> just print status

const PHASE = (typeof PHASE_ARG !== "undefined" && PHASE_ARG) || "status";

// priority per member:  mongo-rs0-1 -> 1 (lowest)   mongo-rs0-2 -> 5 (highest)   mongo-rs0-3 -> 3
const WANT = {
  "mongo-rs0-1:27017": 1,
  "mongo-rs0-2:27017": 5,
  "mongo-rs0-3:27017": 3
};

function showConfig() {
  print("\n=== rs.conf() priorities ===");
  rs.conf().members.forEach(m =>
    print(m.host.padEnd(30) + "priority=" + m.priority + "  votes=" + m.votes));
}
function showStatus(title) {
  print("\n=== " + title + " ===");
  rs.status().members.forEach(m =>
    print(m.name.padEnd(30) + m.stateStr.padEnd(12) + "health=" + m.health));
}
function primaryName() {
  try {
    const p = rs.status().members.find(m => m.stateStr === "PRIMARY");
    return p ? p.name : null;
  } catch (e) { return null; }
}

if (PHASE === "reconfig") {
  const cfg = rs.conf();
  cfg.members.forEach(m => { m.priority = WANT[m.host]; });
  printjson(rs.reconfig(cfg));
  sleep(2000);
  showConfig();

} else if (PHASE === "stepdown") {
  const before = primaryName();
  print("PRIMARY before: " + before);
  print(">>> rs.stepDown(20)");
  const t0 = Date.now();
  try { rs.stepDown(20); }
  catch (e) { print("connection closed by server (expected): " + e.message.substring(0, 60)); }

  let after = null;
  for (let i = 0; i < 80; i++) {
    after = primaryName();
    if (after && after !== before) break;
    after = null;
    sleep(500);
  }
  print(after ? "NEW PRIMARY: " + after + "  (election took ~" +
        ((Date.now() - t0) / 1000).toFixed(1) + " s)"
              : "No new primary within 40 s");
  showStatus("rs.status() after election");

} else {
  showConfig();
  showStatus("rs.status()");
}

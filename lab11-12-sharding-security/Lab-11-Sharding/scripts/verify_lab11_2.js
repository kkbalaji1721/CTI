// Run in mongosh connected to mongos after the Python loader finishes.
const d = db.getSiblingDB("lab11")

print("\n=== Document counts ===")
print("hotspot_data: " + d.hotspot_data.countDocuments({}))
print("even_data: " + d.even_data.countDocuments({}))

print("\n=== Per-shard statistics: hotspot_data ===")
printjson(d.hotspot_data.stats().shards)

print("\n=== Per-shard statistics: even_data ===")
printjson(d.even_data.stats().shards)

print("\n=== Timestamp range query explain ===")
printjson(d.hotspot_data.find({
  ts: {
    $gte: ISODate("2025-01-01T00:00:00Z"),
    $lt: ISODate("2025-01-01T00:30:00Z")
  }
}).explain("executionStats"))

print("\n=== Hashed-field range query explain ===")
printjson(d.even_data.find({
  user_id: {
    $gte: ObjectId("000000000000000000000000"),
    $lt: ObjectId("ffffffffffffffffffffffff")
  }
}).explain("executionStats"))

print("\n=== Shard metadata ===")
sh.status()

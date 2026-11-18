// Run in mongosh connected to mongos.
sh.enableSharding("lab11")
sh.stopBalancer()

// Create the collections and shard them while empty.
// A hashed shard key on an empty collection can be pre-split by MongoDB.
// With the balancer stopped, the lab can observe the initial write placement.
const d = db.getSiblingDB("lab11")
d.hotspot_data.drop()
d.even_data.drop()

sh.shardCollection("lab11.hotspot_data", { ts: 1 })
sh.shardCollection("lab11.even_data", { user_id: "hashed" })

print("Prepared sharded collections. Confirm with sh.status().")

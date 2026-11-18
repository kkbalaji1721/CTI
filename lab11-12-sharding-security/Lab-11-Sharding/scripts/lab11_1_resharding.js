// OPTIONAL demonstration. Run against a demo collection from mongos.
// First create a sample collection with customer_id and shard it on {order_id:1}.
// Resharding can take time and uses extra resources.
const d = db.getSiblingDB("lab11")
d.orders_demo.drop()
d.orders_demo.insertMany([
  { order_id: "O-1", customer_id: "C-1", total: 100 },
  { order_id: "O-2", customer_id: "C-2", total: 200 },
  { order_id: "O-3", customer_id: "C-3", total: 300 }
])
sh.shardCollection("lab11.orders_demo", { order_id: 1 })
print("Before:")
sh.status()

// On supported MongoDB deployments, reshard to hashed customer_id:
sh.reshardCollection("lab11.orders_demo", { customer_id: "hashed" })

print("After:")
sh.status()

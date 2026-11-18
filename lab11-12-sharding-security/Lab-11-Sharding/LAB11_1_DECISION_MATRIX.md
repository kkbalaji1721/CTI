# Lab 11.1 — Evaluate Shard Key Choices

## Workload assumptions
An e-commerce order system commonly performs:
- Customer order history: `customer_id` equality + date sort.
- Order lookup: `order_id` equality.
- Date-based reporting: `order_date` ranges.
- New order inserts continuously.

## Decision matrix

| Candidate | Cardinality | Distribution | Query targeting | Main trade-off |
|---|---|---|---|---|
| `order_id: 1` | Very high if unique | Sequential IDs can concentrate new inserts at the upper range; random IDs distribute better | Excellent only when query includes order_id; customer/date queries may broadcast | Unique order lookup vs. write pattern |
| `customer_id: 1` | Medium to high depending on customer base | Uneven: large customers may own many orders; repeated customer values stay together | Excellent for customer equality and customer history | Customer locality vs. skew/hot customers |
| `order_date: 1` | High at fine timestamp resolution | Monotonically increasing; newest inserts target the newest range/chunk | Good for date-range queries | Date locality vs. write hotspot |
| `customer_id: "hashed"` | High when customer IDs vary | Hashing generally spreads distinct customer values across hash space; each customer's orders still share a shard-key value | Good for equality queries on customer_id; ranges on the hashed key are inefficient | Better distribution vs. loss of useful customer-key range locality |

## Recommendation
For a workload dominated by customer-specific order history and continuous inserts, choose **hashed `customer_id`** as the default among these four candidates. It spreads different customers across the hash space while allowing equality queries on a customer ID to target the owning shard.

This is not universally best. If most requests are direct order-ID lookups, a shard key or compound key beginning with `order_id` may be better. If date-range analytics dominate, consider a compound strategy, time bucketing, or a separate analytics design. A single shard key cannot optimally target every query shape.

## Activity — MongoDB 5.0+ resharding
1. Check the current shard key, indexes, data size, workload and cluster health.
2. Choose a new key and verify that it meets shard-key requirements.
3. Connect to `mongos` and run `sh.reshardCollection()` or `db.adminCommand({reshardCollection: ..., key: ...})`.
4. MongoDB creates recipient-side data, copies existing documents and tracks concurrent changes.
5. Recipient shards build required indexes and apply changes until they catch up.
6. During commit, writes can be briefly blocked and latency can rise; MongoDB commits the new distribution.
7. Verify the new key with `sh.status()` and check distribution and query plans.

Example (run only on a suitable demo collection):
```javascript
sh.reshardCollection("lab11.orders_demo", { customer_id: "hashed" })
```

Limitations and operational cautions:
- Resharding consumes additional CPU, disk, network and temporary storage.
- The operation can increase latency; the commit phase can block writes briefly.
- Do not start it while index builds are running; avoid creating indexes during the operation.
- Queryable Encryption collections are not supported by the reshard command.
- Atlas Search indexes need rebuilding after resharding completes.
- Only one among certain collection-movement operations (including resharding) can run at a time on a cluster.
- Test on a non-production copy and plan capacity and rollback/recovery carefully.

## Conclusion
The best key is selected from the real query mix and write pattern, not cardinality alone. For the stated customer-centric workload, hashed customer_id is the most balanced choice.

// Run as the root administrator after Lab 12.1 MongoDB first starts.
const lab = db.getSiblingDB("lab12");

// Sample data for permission tests.
lab.orders.deleteMany({});
lab.employees.deleteMany({});
lab.orders.insertMany([
  { order_id: "ORD-1001", customer_id: "C-101", status: "shipped" },
  { order_id: "ORD-1002", customer_id: "C-102", status: "processing" }
]);
lab.employees.insertMany([
  { employee_id: "E-01", name: "Asha", department: "Sales", salary: 50000 },
  { employee_id: "E-02", name: "Ravi", department: "IT", salary: 65000 }
]);

// A view omits the salary field. It is not a substitute for protecting the
// underlying collection: users must not receive direct find permission there.
try { lab.dropRole("ordersReader"); } catch (e) {}
try { lab.dropRole("ordersWriter"); } catch (e) {}
try { lab.dropRole("hrPublicReader"); } catch (e) {}

try { lab.dropUser("orders_reader"); } catch (e) {}
try { lab.dropUser("orders_writer"); } catch (e) {}
try { lab.dropUser("hr_reader"); } catch (e) {}

try { lab.dropView("employees_public"); } catch (e) {}
lab.createView("employees_public", "employees", [
  { $project: { _id: 0, employee_id: 1, name: 1, department: 1 } }
]);

lab.createRole({
  role: "ordersReader",
  privileges: [
    { resource: { db: "lab12", collection: "orders_public" }, actions: ["find"] }
  ],
  roles: []
});

lab.createRole({
  role: "ordersWriter",
  privileges: [
    { resource: { db: "lab12", collection: "orders" }, actions: ["find", "insert", "update", "remove"] }
  ],
  roles: []
});

lab.createRole({
  role: "hrPublicReader",
  privileges: [
    { resource: { db: "lab12", collection: "employees_public" }, actions: ["find"] }
  ],
  roles: []
});

// Read-only customer view.
try { lab.dropView("orders_public"); } catch (e) {}
lab.createView("orders_public", "orders", [
  { $project: { _id: 0, order_id: 1, customer_id: 1, status: 1 } }
]);

lab.createUser({
  user: "orders_reader",
  pwd: "ChangeMe_Read_123!",
  roles: [{ role: "ordersReader", db: "lab12" }]
});
lab.createUser({
  user: "orders_writer",
  pwd: "ChangeMe_Write_123!",
  roles: [{ role: "ordersWriter", db: "lab12" }]
});
lab.createUser({
  user: "hr_reader",
  pwd: "ChangeMe_HR_123!",
  roles: [{ role: "hrPublicReader", db: "lab12" }]
});

print("Created lab12 data, views, roles and users.")

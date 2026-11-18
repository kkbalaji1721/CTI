# Lab 12 — MongoDB Security

This folder contains two separate demonstrations.

## Lab 12.1 — Authentication and RBAC
- MongoDB starts with `--auth`.
- Root administrator is created by the official image initialization variables.
- `setup_users.js` creates three least-privilege application users:
  - `orders_reader`: find only on `orders_public` view.
  - `orders_writer`: find/insert/update/remove only on `orders`.
  - `hr_reader`: find only on `employees_public` view.
- `employees_public` excludes `salary`; `hr_reader` cannot query the base `employees` collection.
- Test both allowed and denied actions using the commands in the root README.

The view hides the salary field from users who can only query the view. The base collection must remain inaccessible to those users.

## Lab 12.2 — TLS
Generate a local CA, a server certificate with DNS/IP SANs, and a client certificate. MongoDB is configured with `--tlsMode requireTLS`, a server certificate/key PEM, and the CA certificate. PyMongo uses both the CA and client certificate.

The Python test must show:
1. Plaintext MongoDB connection rejected.
2. TLS connection and ping successful.
3. A TLS-protected insert successful.

These certificates are self-signed classroom certificates only. Do not reuse them in production or publish private keys.

## Reset
For Lab 12.1: `docker compose down -v`
For Lab 12.2: `docker compose -f docker-compose.tls.yml down -v`

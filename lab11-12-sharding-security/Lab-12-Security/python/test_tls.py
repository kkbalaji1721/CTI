from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import PyMongoError

ROOT = Path(__file__).resolve().parents[1]
CERTS = ROOT / "certificates"
URI = "mongodb://localhost:27019"

print("1) Testing a plaintext connection (this should fail)...")
try:
    plain = MongoClient(URI, serverSelectionTimeoutMS=3000)
    plain.admin.command("ping")
    print("UNEXPECTED: plaintext connection succeeded.")
except PyMongoError as exc:
    print("PASS: plaintext connection was rejected.")
    print(type(exc).__name__, str(exc).splitlines()[0][:220])

print("\n2) Testing TLS with the CA and client certificate...")
secure = MongoClient(
    URI,
    tls=True,
    tlsCAFile=str(CERTS / "ca.crt"),
    tlsCertificateKeyFile=str(CERTS / "client.pem"),
    serverSelectionTimeoutMS=8000,
)
try:
    result = secure.admin.command("ping")
    print("PASS: TLS connection succeeded.")
    print("ping:", result)
    secure.get_database("lab12_tls").get_collection("connection_test").insert_one(
        {"test": "TLS connection verified"}
    )
    print("PASS: TLS-protected insert succeeded.")
finally:
    secure.close()

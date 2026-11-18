
"""
Lab 2.1 - Environment Setup Verification
Check all required tools and connections and save results as JSON.
"""

import sys
import os
import subprocess
import json

# Allow Python to find the config folder
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config.connection import banner
from rich.console import Console
from rich.table import Table

console = Console()

# Store all results here
results = {
    "lab": "2.1",
    "title": "Environment Setup Verification",
    "core_components": {},
    "optional_packages": {},
    "summary": {}
}


def check_python_version():
    version = sys.version.split()[0]

    print(f"  Python      : {version}")

    results["core_components"]["Python"] = {
        "version": version,
        "status": "OK"
    }

    return True


def check_pymongo():
    try:
        import pymongo

        version = pymongo.version

        print(f"  PyMongo     : {version}")

        results["core_components"]["PyMongo"] = {
            "version": version,
            "status": "OK"
        }

        return True

    except ImportError:

        print("  PyMongo     : NOT INSTALLED")

        results["core_components"]["PyMongo"] = {
            "version": None,
            "status": "NOT INSTALLED"
        }

        return False


def check_mongo_local():

    try:

        client = MongoClient(
            "mongodb://localhost:27017",
            serverSelectionTimeoutMS=3000
        )

        client.admin.command("ping")

        info = client.server_info()

        version = info["version"]

        print(f"  MongoDB Local: {version} [OK]")

        results["core_components"]["MongoDB Local"] = {
            "version": version,
            "status": "OK",
            "connection": "mongodb://localhost:27017"
        }

        client.close()

        return True

    except Exception as e:

        print("  MongoDB Local: NOT RUNNING")

        results["core_components"]["MongoDB Local"] = {
            "version": None,
            "status": "NOT RUNNING",
            "error": str(e)
        }

        return False


def check_mongo_atlas():

    atlas_uri = os.getenv("MONGO_URI_ATLAS")

    if not atlas_uri:

        print("  MongoDB Atlas: NOT CONFIGURED")

        results["core_components"]["MongoDB Atlas"] = {
            "version": None,
            "status": "NOT CONFIGURED"
        }

        return False

    try:

        client = MongoClient(
            atlas_uri,
            serverSelectionTimeoutMS=5000
        )

        client.admin.command("ping")

        info = client.server_info()

        version = info["version"]

        print(f"  MongoDB Atlas: {version} [OK]")

        results["core_components"]["MongoDB Atlas"] = {
            "version": version,
            "status": "OK"
        }

        client.close()

        return True

    except Exception as e:

        print("  MongoDB Atlas: FAILED")

        results["core_components"]["MongoDB Atlas"] = {
            "version": None,
            "status": "FAILED",
            "error": str(e)
        }

        return False


def check_docker():

    try:

        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:

            docker_version = result.stdout.strip()

            print(f"  Docker      : {docker_version}")

            ps = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "ancestor=mongo:7",
                    "--format",
                    "{{.Names}}"
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            container_name = ps.stdout.strip()

            if container_name:

                print(
                    f"  Mongo Container: Running ({container_name})"
                )

                container_status = "RUNNING"

            else:

                print("  Mongo Container: NOT RUNNING")

                container_status = "NOT RUNNING"

            results["core_components"]["Docker"] = {
                "version": docker_version,
                "status": "OK",
                "mongo_container": container_name
                if container_name else None,
                "container_status": container_status
            }

            return True

    except (FileNotFoundError, subprocess.TimeoutExpired):

        print("  Docker      : NOT INSTALLED")

        results["core_components"]["Docker"] = {
            "version": None,
            "status": "NOT INSTALLED"
        }

        return False

    return False


def check_optional_packages():

    optional = [
        "fastapi",
        "streamlit",
        "voyageai",
        "neo4j",
        "cassandra",
        "rich",
        "dotenv"
    ]

    for pkg in optional:

        try:

            __import__(pkg)

            print(f"  {pkg:16} : installed")

            results["optional_packages"][pkg] = "installed"

        except ImportError:

            print(
                f"  {pkg:16} : not installed (optional)"
            )

            results["optional_packages"][pkg] = "not installed"


def save_json():

    # Save JSON one level above the code folder
    base_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    json_file = os.path.join(
        base_dir,
        "lab_01_setup_environment.json"
    )

    with open(
        json_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    print()
    print(f"[OK] JSON result saved to:")
    print(json_file)


def main():

    banner("Lab 2.1: Environment Setup Verification")

    print("Core Components:")

    checks = [
        ("Python", check_python_version),
        ("PyMongo", check_pymongo),
        ("MongoDB Local", check_mongo_local),
        ("MongoDB Atlas", check_mongo_atlas),
        ("Docker", check_docker),
    ]

    passed = 0

    for name, fn in checks:

        if fn():
            passed += 1

    print("\nOptional Packages:")

    check_optional_packages()

    print("\n--- Summary ---")

    total = len(checks)

    print(f"  Core checks passed: {passed}/{total}")

    if passed >= 3:

        print("  [OK] You are ready to start the labs!")

        overall_status = "READY"

    else:

        print(
            "  [WARN] Some required components are missing."
        )

        overall_status = "NOT READY"

    results["summary"] = {
        "core_checks_passed": passed,
        "core_checks_total": total,
        "overall_status": overall_status
    }

    # Save everything as JSON
    save_json()

    banner("Lab 2.1 Complete")


if __name__ == "__main__":
    main()
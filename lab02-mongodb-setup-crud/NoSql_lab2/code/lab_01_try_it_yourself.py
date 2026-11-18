
"""
Lab 2.1 - Try It Yourself
Compare Local/Docker MongoDB and MongoDB Atlas
using server_info().

The comparison results are also saved as JSON.
"""

import os
import sys
import json

from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Allow Python to find the config folder
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config.connection import banner


# Store comparison results
results = {
    "lab": "2.1",
    "title": "MongoDB Server Comparison - Try It Yourself",
    "local_docker": {},
    "atlas": {},
    "version_comparison": {}
}


def get_local_server_info():

    print("Connecting to Local/Docker MongoDB...")

    try:

        client = MongoClient(
            "mongodb://localhost:27017",
            serverSelectionTimeoutMS=5000
        )

        # Test connection
        client.admin.command("ping")

        # Get server information
        info = client.server_info()

        print("[OK] Local/Docker MongoDB connection successful")

        results["local_docker"] = {
            "connection": "mongodb://localhost:27017",
            "status": "CONNECTED",
            "version": info.get("version"),
            "git_version": info.get("gitVersion"),
            "modules": info.get("modules", []),
            "storage_engines": info.get("storageEngines", [])
        }

        client.close()

        return info

    except Exception as e:

        print("[ERROR] Could not connect to Local/Docker MongoDB")
        print(f"Details: {e}")

        results["local_docker"] = {
            "connection": "mongodb://localhost:27017",
            "status": "FAILED",
            "error": str(e)
        }

        return None


def get_atlas_server_info():

    print("\nConnecting to MongoDB Atlas...")

    atlas_uri = os.getenv("MONGO_URI_ATLAS")

    if not atlas_uri:

        print("[WARN] MONGO_URI_ATLAS is not configured.")
        print("Set the MONGO_URI_ATLAS environment variable.")

        results["atlas"] = {
            "status": "NOT CONFIGURED"
        }

        return None

    try:

        client = MongoClient(
            atlas_uri,
            serverSelectionTimeoutMS=10000
        )

        # Test connection
        client.admin.command("ping")

        # Get server information
        info = client.server_info()

        print("[OK] MongoDB Atlas connection successful")

        results["atlas"] = {
            "status": "CONNECTED",
            "version": info.get("version"),
            "git_version": info.get("gitVersion"),
            "modules": info.get("modules", []),
            "storage_engines": info.get("storageEngines", [])
        }

        client.close()

        return info

    except Exception as e:

        print("[ERROR] Could not connect to MongoDB Atlas")
        print(f"Details: {e}")

        results["atlas"] = {
            "status": "FAILED",
            "error": str(e)
        }

        return None


def compare_versions(local_info, atlas_info):

    print("\n" + "=" * 70)
    print("VERSION COMPARISON")
    print("=" * 70)

    if local_info and atlas_info:

        local_version = local_info.get("version")
        atlas_version = atlas_info.get("version")

        if local_version == atlas_version:

            print("[OK] MongoDB versions are the same.")

            comparison = "SAME"

        else:

            print("[INFO] MongoDB versions are different.")
            print(f"Local/Docker : {local_version}")
            print(f"Atlas        : {atlas_version}")

            comparison = "DIFFERENT"

        results["version_comparison"] = {
            "local_docker_version": local_version,
            "atlas_version": atlas_version,
            "comparison": comparison
        }

    elif local_info:

        print("[WARN] Local/Docker MongoDB connected.")
        print("Atlas connection is not available.")

        results["version_comparison"] = {
            "local_docker_version": local_info.get("version"),
            "atlas_version": None,
            "comparison": "ATLAS NOT AVAILABLE"
        }

    elif atlas_info:

        print("[WARN] Atlas MongoDB connected.")
        print("Local/Docker connection is not available.")

        results["version_comparison"] = {
            "local_docker_version": None,
            "atlas_version": atlas_info.get("version"),
            "comparison": "LOCAL/DOCKER NOT AVAILABLE"
        }

    else:

        print("[ERROR] Neither MongoDB server is available.")

        results["version_comparison"] = {
            "local_docker_version": None,
            "atlas_version": None,
            "comparison": "NO CONNECTION"
        }


def display_comparison(local_info, atlas_info):

    print("\n" + "=" * 70)
    print("SERVER INFORMATION COMPARISON")
    print("=" * 70)

    print(
        f"{'Information':25}"
        f"{'Local/Docker':25}"
        f"{'Atlas':25}"
    )

    print("-" * 75)

    local_version = (
        local_info.get("version")
        if local_info
        else None
    )

    atlas_version = (
        atlas_info.get("version")
        if atlas_info
        else None
    )

    local_git = (
        local_info.get("gitVersion")
        if local_info
        else None
    )

    atlas_git = (
        atlas_info.get("gitVersion")
        if atlas_info
        else None
    )

    local_modules = (
        local_info.get("modules", [])
        if local_info
        else None
    )

    atlas_modules = (
        atlas_info.get("modules", [])
        if atlas_info
        else None
    )

    local_storage = (
        local_info.get("storageEngines", [])
        if local_info
        else None
    )

    atlas_storage = (
        atlas_info.get("storageEngines", [])
        if atlas_info
        else None
    )

    print(
        f"{'Version':25}"
        f"{str(local_version):25}"
        f"{str(atlas_version):25}"
    )

    print(
        f"{'Git Version':25}"
        f"{str(local_git):25}"
        f"{str(atlas_git):25}"
    )

    print(
        f"{'Modules':25}"
        f"{str(local_modules):25}"
        f"{str(atlas_modules):25}"
    )

    print(
        f"{'Storage Engines':25}"
        f"{str(local_storage):25}"
        f"{str(atlas_storage):25}"
    )


def save_json():

    # Main NoSql_lab2 folder
    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    json_file = os.path.join(
        base_dir,
        "lab_01_try_it_yourself.json"
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

    print("\n[OK] JSON result saved to:")
    print(json_file)


def main():

    banner(
        "Lab 2.1 Try It Yourself: MongoDB Server Comparison"
    )

    print(
        "Checking Local/Docker MongoDB and MongoDB Atlas..."
    )

    # Get server information
    local_info = get_local_server_info()

    atlas_info = get_atlas_server_info()

    # Display comparison
    print("\n" + "=" * 70)
    print("SERVER INFORMATION COMPARISON")
    print("=" * 70)

    display_comparison(
        local_info,
        atlas_info
    )

    # Compare versions
    compare_versions(
        local_info,
        atlas_info
    )

    # Save JSON
    save_json()

    banner(
        "Lab 2.1 Try It Yourself Complete"
    )


if __name__ == "__main__":
    main()


#!/usr/bin/env bash
# Usage: ./push_to_github.sh https://github.com/<username>/<repo>.git
set -e
[ -z "$1" ] && { echo "Usage: $0 <github-repo-url>"; exit 1; }
git remote remove origin 2>/dev/null || true
git remote add origin "$1"
git branch -M main
git push -u origin main

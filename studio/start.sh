#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
echo "🎬 CrowdListen Studio"
echo "Installing dependencies..."
pip install -r requirements.txt -q
echo ""
echo "→ http://localhost:8000"
echo ""
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

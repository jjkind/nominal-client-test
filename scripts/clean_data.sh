#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="data"

if [ ! -d "$DATA_DIR" ]; then
  echo "Data directory not found: $DATA_DIR"
  exit 1
fi

echo "Deleting all files under $DATA_DIR except .gitkeep files..."

find "$DATA_DIR" -type f ! -name ".gitkeep" -print -delete

echo "Done."
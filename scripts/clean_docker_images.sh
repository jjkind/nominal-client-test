#!/usr/bin/env bash
set -euo pipefail

echo "This will delete unused Docker images."
echo "It will NOT delete running containers or Docker volumes."
echo

docker image prune -a -f

echo
echo "Docker image cleanup complete."
docker images
#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_root"

command -v docker >/dev/null 2>&1 || { echo "docker CLI is required" >&2; exit 69; }
docker compose version >/dev/null
docker compose --profile standalone config --quiet
docker compose --profile standalone up --build --wait

host_bind=${ASKLILY_HOST_BIND:-127.0.0.1}
host_port=${ASKLILY_HOST_PORT:-8080}
curl --fail --silent --show-error --retry 5 "http://${host_bind}:${host_port}/health" >/dev/null
echo "standalone upgrade completed; health endpoint is reachable"

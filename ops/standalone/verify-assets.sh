#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_root"

for required in compose.yaml Dockerfile.api Dockerfile.web deploy/standalone/nginx.conf deploy/standalone/.env.example; do
  test -f "$required" || { echo "missing required standalone asset: $required" >&2; exit 1; }
done

grep -Fq 'ASKLILY_RUNTIME_PROFILE: standalone' compose.yaml
grep -Fq '127.0.0.1}:${ASKLILY_HOST_PORT:-8080}:8080' compose.yaml
grep -Fq 'no-new-privileges:true' compose.yaml
grep -Fq 'cap_drop:' compose.yaml
grep -Fq 'proxy_pass http://api:8000' deploy/standalone/nginx.conf

if git ls-files | grep -Eq '(^|/)(\.env|secrets/|.*\.(pem|key|p12|pfx))$'; then
  echo "tracked secret-shaped file found" >&2
  exit 1
fi

echo "P4 standalone assets pass offline policy validation"

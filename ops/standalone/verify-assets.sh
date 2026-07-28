#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_root"

for required in compose.yaml Dockerfile.api Dockerfile.web deploy/standalone/nginx.conf deploy/standalone/.env.example; do
  test -f "$required" || { echo "missing required standalone asset: $required" >&2; exit 1; }
done

! grep -Fq 'ASKLILY_RUNTIME_PROFILE' compose.yaml
grep -Fq 'storage-init:' compose.yaml
grep -Fq 'asklily_data:/var/lib/asklily' compose.yaml
grep -Fq 'service_completed_successfully' compose.yaml
grep -Fq '127.0.0.1:${ASKLILY_HOST_PORT:-8080}:8080' compose.yaml
grep -Fq 'no-new-privileges:true' compose.yaml
grep -Fq 'cap_drop:' compose.yaml
grep -Fq 'resolver 127.0.0.11' deploy/standalone/nginx.conf
grep -Fq 'proxy_pass http://$api_upstream' deploy/standalone/nginx.conf
if grep -Fq 'ASKLILY_HOST_BIND' compose.yaml deploy/standalone/.env.example ops/standalone/upgrade.sh; then
  echo "standalone host bind must be fixed to loopback" >&2
  exit 1
fi

if git ls-files | grep -Eq '(^|/)(\.env|secrets/|.*\.(pem|key|p12|pfx))$'; then
  echo "tracked secret-shaped file found" >&2
  exit 1
fi

echo "P6 unified runtime assets pass offline policy validation"

#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 BACKUP_DIRECTORY" >&2
  exit 64
fi

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
destination=$1
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$destination/asklily-standalone-$timestamp.tar.gz"
manifest="$destination/asklily-standalone-$timestamp.sha256"
workdir=$(mktemp -d "${TMPDIR:-/tmp}/asklily-backup.XXXXXX")
trap 'rm -rf "$workdir"' EXIT HUP INT TERM

umask 077
mkdir -p "$destination" "$workdir/asklily-standalone"
cd "$repo_root"

git ls-files -- \
  compose.yaml Dockerfile.api Dockerfile.web .dockerignore \
  deploy/standalone ops/standalone docs/adr docs/runbooks docs/capabilities/P4-STANDALONE-brief.md \
  | while IFS= read -r path; do
      test -n "$path" || continue
      case "$path" in
        *.env.example)
          ;;
        *.env|*.env.*|*.pem|*.key|*.p12|*.pfx|secrets/*|credentials*)
          echo "refusing secret-shaped path in backup selection: $path" >&2
          exit 1
          ;;
      esac
      mkdir -p "$workdir/asklily-standalone/$(dirname -- "$path")"
      cp "$path" "$workdir/asklily-standalone/$path"
    done

printf 'kind=stateless_deployment_bundle\nsource_commit=%s\ncreated_at=%s\n' \
  "$(git rev-parse HEAD)" "$timestamp" > "$workdir/asklily-standalone/RESTORE-METADATA.txt"
tar -C "$workdir" -czf "$archive" asklily-standalone

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$archive" > "$manifest"
else
  shasum -a 256 "$archive" > "$manifest"
fi

echo "created non-secret stateless deployment backup: $archive"
echo "checksum manifest: $manifest"

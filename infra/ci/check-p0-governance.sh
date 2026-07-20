#!/usr/bin/env bash
# P0 L0 governance gate.  This check is intentionally offline: it examines
# only the checked-out repository and never starts a service or changes data.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  printf '%s\n' 'ERROR: must be run inside a Git worktree.' >&2
  exit 2
}
cd "$repo_root"

failures=0

require_directory() {
  local path="$1"
  if [[ -d "$path" ]]; then
    printf 'OK directory: %s\n' "$path"
  else
    printf 'ERROR missing required directory: %s\n' "$path" >&2
    failures=1
  fi
}

require_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    printf 'OK file: %s\n' "$path"
  else
    printf 'ERROR missing required file: %s\n' "$path" >&2
    failures=1
  fi
}

require_ignored() {
  local path="$1"
  if git check-ignore -q --no-index "$path"; then
    printf 'OK ignored: %s\n' "$path"
  else
    printf 'ERROR .gitignore does not ignore required local artefact: %s\n' "$path" >&2
    failures=1
  fi
}

printf '%s\n' 'P0 L0 governance check (offline; no services, data writes, downloads, or network access)'

# P0 project skeleton.  Empty directories must contain a tracked placeholder.
for required_dir in apps services packages connectors tests infra docs docs/adr docs/governance docs/templates .github .github/ISSUE_TEMPLATE .github/workflows; do
  require_directory "$required_dir"
done

# P0 governance artefacts required by the construction baseline.
for required_file in \
  .gitignore \
  .gitattributes \
  CONTRIBUTING.md \
  .github/ISSUE_TEMPLATE/task-protocol.md \
  docs/governance/README.md \
  docs/governance/collaboration-policy.md \
  docs/governance/task-status.md \
  docs/governance/risk-change-review.md \
  docs/adr/README.md \
  docs/adr/0000-template.md \
  docs/templates/README.md \
  docs/templates/capability-brief.md \
  docs/templates/capability-manifest.yaml \
  docs/templates/feature-completion-package.md; do
  require_file "$required_file"
done

# P0 must protect common local credentials, build artefacts, test output, and
# IDE state.  Check representative paths so the rules remain reviewable.
for ignored_path in \
  .env \
  .env.local \
  secrets/local.pem \
  .venv/bin/python \
  __pycache__/module.pyc \
  node_modules/package.json \
  dist/app.js \
  coverage/lcov.info \
  .idea/workspace.xml; do
  require_ignored "$ignored_path"
done

if git check-ignore -q --no-index .env.example; then
  printf '%s\n' 'ERROR .env.example must remain trackable as the safe configuration example.' >&2
  failures=1
else
  printf '%s\n' 'OK trackable: .env.example'
fi

# .env.example documents configuration shape and is safe to track.  Other
# .env files, common credential files, and private-key file extensions are not.
while IFS= read -r -d '' tracked_file; do
  case "$tracked_file" in
    .env.example|*/.env.example)
      ;;
    .env|.env.*|*/.env|*/.env.*|*.env|*.pem|*.key|*.p12|*.pfx|*/credentials|*/credentials.*|credentials|credentials.*)
      printf 'ERROR tracked environment or credential file: %s\n' "$tracked_file" >&2
      failures=1
      ;;
  esac
done < <(git ls-files -z)

if (( failures != 0 )); then
  printf '%s\n' 'P0 L0 governance check FAILED. Resolve every ERROR above before merge.' >&2
  exit 1
fi

printf '%s\n' 'P0 L0 governance check PASSED.'

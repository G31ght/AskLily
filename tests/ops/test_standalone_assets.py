from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_standalone_assets_keep_the_api_private_and_the_web_loopback_bound() -> None:
    compose = (REPOSITORY_ROOT / "compose.yaml").read_text()
    nginx = (REPOSITORY_ROOT / "deploy/standalone/nginx.conf").read_text()
    assert 'ASKLILY_RUNTIME_PROFILE: standalone' in compose
    assert '127.0.0.1}:${ASKLILY_HOST_PORT:-8080}:8080' in compose
    assert 'condition: service_healthy' in compose
    assert 'internal: true' in compose
    assert 'no-new-privileges:true' in compose
    assert 'proxy_pass http://api:8000' in nginx
    assert 'ports:' not in compose.split('\n  web:', maxsplit=1)[0]


def test_backup_creates_a_non_secret_stateless_deployment_bundle(tmp_path: Path) -> None:
    result = subprocess.run(
        ["sh", "ops/standalone/backup.sh", str(tmp_path)],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "non-secret stateless deployment backup" in result.stdout
    archive = next(tmp_path.glob("asklily-standalone-*.tar.gz"))
    checksum = next(tmp_path.glob("asklily-standalone-*.sha256"))
    assert checksum.read_text().strip()
    with tarfile.open(archive) as bundle:
        members = bundle.getnames()
    assert "asklily-standalone/compose.yaml" in members
    assert "asklily-standalone/RESTORE-METADATA.txt" in members
    assert not any(member.endswith("/.env") or "/secrets/" in member for member in members)

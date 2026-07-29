from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_unified_runtime_assets_keep_the_api_private_and_the_web_loopback_bound() -> None:
    compose = (REPOSITORY_ROOT / "compose.yaml").read_text()
    nginx = (REPOSITORY_ROOT / "deploy/standalone/nginx.conf").read_text()
    assert 'ASKLILY_RUNTIME_PROFILE' not in compose
    assert 'storage-init:' in compose
    assert 'asklily_data:/var/lib/asklily' in compose
    assert 'service_completed_successfully' in compose
    assert '127.0.0.1:${ASKLILY_HOST_PORT:-8080}:8080' in compose
    assert 'condition: service_healthy' in compose
    assert 'internal: true' in compose
    assert 'no-new-privileges:true' in compose
    assert 'ASKLILY_HOST_BIND' not in compose
    assert 'ASKLILY_HOST_BIND' not in (REPOSITORY_ROOT / 'deploy/standalone/.env.example').read_text()
    assert 'resolver 127.0.0.11' in nginx
    assert 'proxy_pass http://$api_upstream' in nginx
    assert 'ports:' not in compose.split('\n  web:', maxsplit=1)[0]
    assert 'asklily_edge' in compose


def test_backup_creates_a_non_secret_runtime_deployment_bundle(tmp_path: Path) -> None:
    result = subprocess.run(
        ["sh", "ops/standalone/backup.sh", str(tmp_path)],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "non-secret runtime deployment backup" in result.stdout
    archive = next(tmp_path.glob("asklily-runtime-*.tar.gz"))
    checksum = next(tmp_path.glob("asklily-runtime-*.sha256"))
    assert checksum.read_text().strip()
    with tarfile.open(archive) as bundle:
        members = bundle.getnames()
    assert "asklily-runtime/compose.yaml" in members
    assert "asklily-runtime/RESTORE-METADATA.txt" in members
    assert not any(member.endswith("/.env") or "/secrets/" in member for member in members)

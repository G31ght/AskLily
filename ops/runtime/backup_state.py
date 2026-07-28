#!/usr/bin/env python3
"""Create a local, consistent SQLite control-plane backup without exporting rows."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: backup_state.py DATABASE_PATH BACKUP_DIRECTORY", file=sys.stderr)
        return 64
    source = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2]).resolve()
    if not source.is_file():
        print("database path must be an existing regular file", file=sys.stderr)
        return 66
    destination.mkdir(parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = destination / f"asklily-platform-state-{stamp}.sqlite3"
    checksum = backup.with_suffix(".sqlite3.sha256")
    try:
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_connection:
            with sqlite3.connect(backup) as backup_connection:
                source_connection.backup(backup_connection)
                result = backup_connection.execute("PRAGMA quick_check").fetchone()
        if result is None or str(result[0]) != "ok":
            raise sqlite3.DatabaseError("backup_integrity_check_failed")
    except (OSError, sqlite3.Error) as exc:
        backup.unlink(missing_ok=True)
        print(f"sqlite backup failed: {exc}", file=sys.stderr)
        return 74
    os.chmod(backup, 0o600)
    checksum.write_text(f"{hashlib.sha256(backup.read_bytes()).hexdigest()}  {backup.name}\n", encoding="utf-8")
    os.chmod(checksum, 0o600)
    print(f"created local control-plane backup: {backup}")
    print(f"checksum manifest: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

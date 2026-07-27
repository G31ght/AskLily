"""Local-only account, server-session and conversation persistence for P5B.

This module never contacts an identity provider or a remote datastore.  It uses
SQLite only after an account operation is requested; the existing Fixture demo
therefore stays usable in its legacy developer path until P5B is enabled.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from asklily_contracts import Scope

USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")
SESSION_TTL = timedelta(hours=12)


class IdentityError(ValueError):
    """A safe authentication, authorization or persistence failure."""


@dataclass(frozen=True)
class LocalIdentity:
    account_id: str
    username: str
    display_name: str
    role: str
    scope: Scope


def default_database_path(environment: dict[str, str] | None = None) -> Path:
    values = os.environ if environment is None else environment
    configured = values.get("ASKLILY_LOCAL_DATA_DIR", "data").strip()
    if not configured:
        raise IdentityError("local_data_directory_required")
    return Path(configured) / "asklily-local.sqlite3"


class LocalIdentityStore:
    def __init__(self, database_path: Path) -> None:
        self._path = database_path

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    site_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                    project_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    title TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                    author TEXT NOT NULL CHECK(author IN ('user', 'assistant')),
                    body TEXT NOT NULL,
                    source_label TEXT,
                    limitation_label TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def register(self, username: str, password: str, display_name: str | None = None) -> LocalIdentity:
        self.initialize()
        if not USERNAME.fullmatch(username):
            raise IdentityError("local_username_invalid")
        if len(password) < 12 or len(password) > 128:
            raise IdentityError("local_password_length_invalid")
        identity = LocalIdentity(
            account_id=f"acct-{secrets.token_urlsafe(18)}",
            username=username,
            display_name=display_name.strip() if display_name and display_name.strip() else username,
            role="operator",
            scope=Scope("demo-project", frozenset({"site-a"}), actions=frozenset({"read"})),
        )
        now = _now()
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (identity.account_id, identity.username, identity.display_name, _hash_password(password), identity.role,
                     identity.scope.project_id, ",".join(sorted(identity.scope.site_ids)), now),
                )
        except sqlite3.IntegrityError as exc:
            raise IdentityError("local_username_already_exists") from exc
        return identity

    def authenticate(self, username: str, password: str) -> LocalIdentity:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE username = ?", (username,)).fetchone()
        if row is None or not _verify_password(password, str(row["password_hash"])):
            raise IdentityError("local_credentials_invalid")
        return _identity_from_row(row)

    def issue_session(self, account_id: str) -> str:
        self.initialize()
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now.isoformat(),))
            connection.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", (_digest(token), account_id, (now + SESSION_TTL).isoformat(), now.isoformat()))
        return token

    def resolve_session(self, token: str) -> LocalIdentity:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT accounts.* FROM sessions JOIN accounts USING(account_id) WHERE token_hash = ? AND expires_at > ?",
                (_digest(token), _now()),
            ).fetchone()
        if row is None:
            raise IdentityError("local_session_invalid_or_expired")
        return _identity_from_row(row)

    def revoke_session(self, token: str) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_digest(token),))

    def create_or_append_conversation(
        self, identity: LocalIdentity, conversation_id: str | None, question: str, answer: str, source: str, limitation: str
    ) -> str:
        self.initialize()
        now = _now()
        with self._connect() as connection:
            if conversation_id is None:
                conversation_id = f"conv-{secrets.token_urlsafe(18)}"
                connection.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)", (conversation_id, identity.account_id, identity.scope.project_id, now, now, question[:120]))
            else:
                owner = connection.execute("SELECT account_id, project_id FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
                if owner is None or owner["account_id"] != identity.account_id or owner["project_id"] != identity.scope.project_id:
                    raise IdentityError("conversation_not_found")
                connection.execute("UPDATE conversations SET updated_at = ?, title = ? WHERE conversation_id = ?", (now, question[:120], conversation_id))
            for author, body, item_source, item_limitation in (("user", question, None, None), ("assistant", answer, source, limitation)):
                connection.execute("INSERT INTO conversation_messages VALUES (?, ?, ?, ?, ?, ?, ?)", (f"msg-{secrets.token_urlsafe(18)}", conversation_id, author, body, item_source, item_limitation, now))
        return conversation_id

    def list_conversations(self, identity: LocalIdentity) -> list[dict[str, str]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute("SELECT conversation_id, title, updated_at FROM conversations WHERE account_id = ? AND project_id = ? ORDER BY updated_at DESC", (identity.account_id, identity.scope.project_id)).fetchall()
        return [dict(row) for row in rows]

    def read_conversation(self, identity: LocalIdentity, conversation_id: str) -> dict[str, object]:
        self.initialize()
        with self._connect() as connection:
            conversation = connection.execute("SELECT conversation_id, title, updated_at FROM conversations WHERE conversation_id = ? AND account_id = ? AND project_id = ?", (conversation_id, identity.account_id, identity.scope.project_id)).fetchone()
            if conversation is None:
                raise IdentityError("conversation_not_found")
            messages = connection.execute("SELECT author, body, source_label, limitation_label, created_at FROM conversation_messages WHERE conversation_id = ? ORDER BY created_at, rowid", (conversation_id,)).fetchall()
        return {**dict(conversation), "messages": [dict(row) for row in messages]}

    def delete_conversation(self, identity: LocalIdentity, conversation_id: str) -> None:
        self.initialize()
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM conversations WHERE conversation_id = ? AND account_id = ? AND project_id = ?", (conversation_id, identity.account_id, identity.scope.project_id))
        if cursor.rowcount != 1:
            raise IdentityError("conversation_not_found")

    def delete_account(self, identity: LocalIdentity, password: str) -> None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute("SELECT password_hash FROM accounts WHERE account_id = ?", (identity.account_id,)).fetchone()
            if row is None or not _verify_password(password, str(row["password_hash"])):
                raise IdentityError("local_credentials_invalid")
            connection.execute("DELETE FROM accounts WHERE account_id = ?", (identity.account_id,))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(derived).decode()


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=base64.urlsafe_b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


def _identity_from_row(row: sqlite3.Row) -> LocalIdentity:
    return LocalIdentity(str(row["account_id"]), str(row["username"]), str(row["display_name"]), str(row["role"]), Scope(str(row["project_id"]), frozenset(filter(None, str(row["site_ids"]).split(","))), actions=frozenset({"read"})))

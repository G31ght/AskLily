"""Local-only bootstrap for the first AskLily project administrator.

Run on the host terminal: ``python -m asklily_api.admin_bootstrap``.
The command deliberately reads the password interactively and never accepts it
from command-line arguments or environment variables.
"""

from __future__ import annotations

import getpass

from .local_identity import IdentityError, LocalIdentityStore, default_database_path


def main() -> int:
    print("AskLily 本地项目管理员初始化（仅本机）")
    username = input("管理员账号：").strip()
    display_name = input("显示名称（可留空）：").strip() or None
    password = getpass.getpass("管理员密码：")
    confirmation = getpass.getpass("再次输入密码：")
    if password != confirmation:
        print("初始化失败：两次密码不一致")
        return 2
    try:
        identity = LocalIdentityStore(default_database_path()).bootstrap_project_admin(username, password, display_name)
    except IdentityError as exc:
        print(f"初始化失败：{exc}")
        return 2
    print(f"初始化完成：{identity.username}（{identity.role}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""Persistent, transactional replay guard for authenticated commands."""
from __future__ import annotations
import re
import sqlite3
import time

IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class ReplayStore:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS replay(
            device_id TEXT NOT NULL, command_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            PRIMARY KEY(device_id,command_id)
        )""")

    def reserve(self, device_id: str, command_id: str, expires_at: int) -> bool:
        if (not isinstance(device_id, str) or not IDENTIFIER.fullmatch(device_id) or
            not isinstance(command_id, str) or not IDENTIFIER.fullmatch(command_id) or
            type(expires_at) is not int):
            raise ValueError("Invalid replay metadata")
        now = int(time.time())
        if expires_at < now or expires_at > now + 300:
            return False
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("DELETE FROM replay WHERE expires_at < ?", (now,))
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO replay(device_id,command_id,expires_at) VALUES(?,?,?)",
                (device_id, command_id, expires_at),
            )
            self.db.execute("COMMIT")
            return cursor.rowcount == 1
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def close(self):
        self.db.close()

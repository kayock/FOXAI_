from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Vault:
    foxai_root: Path

    @property
    def vault_root(self) -> Path:
        path = Path(self.foxai_root) / "Vault"
        path.mkdir(parents=True, exist_ok=True)
        (path / "backups").mkdir(parents=True, exist_ok=True)
        (path / "logs").mkdir(parents=True, exist_ok=True)
        (path / "exports").mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        return self.vault_root / "FOXAI.db"

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self) -> dict[str, Any]:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_info (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL,
                created TEXT NOT NULL,
                updated TEXT NOT NULL,
                foxai_version TEXT
            );

            INSERT OR IGNORE INTO schema_info (id, version, created, updated, foxai_version)
            VALUES (1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'CM v2.4');

            UPDATE schema_info
            SET updated = CURRENT_TIMESTAMP
            WHERE id = 1;

            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created TEXT NOT NULL,
                updated TEXT NOT NULL,
                title TEXT NOT NULL,
                request TEXT,
                professor TEXT,
                mission_type TEXT,
                department TEXT,
                status TEXT NOT NULL DEFAULT 'planned'
            );

            CREATE TABLE IF NOT EXISTS mission_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                capability TEXT,
                shuttle_key TEXT,
                shuttle_callsign TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                details TEXT,
                created TEXT NOT NULL,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS mission_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER,
                created TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'INFO',
                source TEXT NOT NULL DEFAULT 'MissionBus',
                message TEXT NOT NULL,
                data TEXT,
                FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE SET NULL
            );
            """)
            row = conn.execute("SELECT version, created, updated, foxai_version FROM schema_info WHERE id = 1").fetchone()

        return {
            "ok": True,
            "vault": str(self.vault_root),
            "db": str(self.db_path),
            "schema": dict(row) if row else None,
        }

    def log_mission(self, title: str, request: str = "", professor: str = "", mission_type: str = "", department: str = "", status: str = "planned") -> dict[str, Any]:
        self.initialize()
        ts = now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO missions (created, updated, title, request, professor, mission_type, department, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, ts, title, request, professor, mission_type, department, status),
            )
            mission_id = int(cur.lastrowid)
        return {"ok": True, "mission_id": mission_id}

    def log_step(self, mission_id: int, step_number: int, capability: str = "", shuttle_key: str = "", shuttle_callsign: str = "", status: str = "planned", details: str = "") -> dict[str, Any]:
        self.initialize()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO mission_steps (mission_id, step_number, capability, shuttle_key, shuttle_callsign, status, details, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mission_id, step_number, capability, shuttle_key, shuttle_callsign, status, details, now()),
            )
            step_id = int(cur.lastrowid)
        return {"ok": True, "step_id": step_id}

    def log_event(self, message: str, mission_id: int | None = None, level: str = "INFO", source: str = "MissionBus", data: str = "") -> dict[str, Any]:
        self.initialize()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO mission_logs (mission_id, created, level, source, message, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mission_id, now(), level, source, message, data),
            )
            log_id = int(cur.lastrowid)
        return {"ok": True, "log_id": log_id}

    def list_missions(self, limit: int = 20) -> dict[str, Any]:
        self.initialize()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created, updated, title, request, professor, mission_type, department, status
                FROM missions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return {"ok": True, "missions": [dict(r) for r in rows]}

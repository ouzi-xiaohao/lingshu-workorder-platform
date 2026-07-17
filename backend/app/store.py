from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator


class WorkOrderStore:
    def __init__(self, path: str = "data/lingshu.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                    category TEXT NOT NULL, area TEXT NOT NULL, priority TEXT NOT NULL,
                    status TEXT NOT NULL, reporter TEXT NOT NULL, assignee TEXT,
                    confidence REAL NOT NULL, attachments TEXT NOT NULL DEFAULT '[]',
                    trace_id TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, work_order_id TEXT NOT NULL,
                    agent TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    def create(self, item: dict[str, object]) -> dict[str, object]:
        columns = tuple(item.keys())
        values = [json.dumps(value, ensure_ascii=False) if key == "attachments" else value for key, value in item.items()]
        with self._lock, self.connection() as conn:
            conn.execute(f"INSERT INTO work_orders ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", values)
        return item

    def list(self, status: str | None = None) -> list[dict[str, object]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM work_orders WHERE (? IS NULL OR status = ?) ORDER BY created_at DESC", (status, status)).fetchall()
        return [self._decode(row) for row in rows]

    def get(self, work_order_id: str) -> dict[str, object] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
        return self._decode(row) if row else None

    def assign(self, work_order_id: str, assignee: str) -> dict[str, object] | None:
        with self._lock, self.connection() as conn:
            conn.execute("UPDATE work_orders SET assignee = ?, status = '处理中' WHERE id = ? AND (assignee IS NULL OR assignee = '')", (assignee, work_order_id))
        return self.get(work_order_id)

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, object]:
        item = dict(row)
        item["attachments"] = json.loads(str(item["attachments"]))
        return item

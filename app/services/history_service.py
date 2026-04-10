import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryService:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS detection_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    result_label TEXT NOT NULL,
                    score REAL NOT NULL,
                    source_path TEXT NOT NULL,
                    result_json_path TEXT NOT NULL,
                    preview_path TEXT,
                    created_at TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    inference_time REAL NOT NULL
                );
                """
            )
            self._ensure_column(conn, "batch_task_id", "TEXT")
            self._ensure_column(conn, "batch_name", "TEXT")
            self._ensure_column(conn, "batch_size", "INTEGER")
            self._ensure_column(conn, "batch_index", "INTEGER")
            conn.execute(
                """
                UPDATE detection_records
                SET
                    batch_task_id = COALESCE(NULLIF(batch_task_id, ''), task_id),
                    batch_name = COALESCE(NULLIF(batch_name, ''), file_name),
                    batch_size = COALESCE(batch_size, 1),
                    batch_index = COALESCE(batch_index, 1)
                """
            )
            conn.commit()

    def _ensure_column(self, conn: sqlite3.Connection, column_name: str, definition: str) -> None:
        cur = conn.execute("PRAGMA table_info(detection_records)")
        columns = {row[1] for row in cur.fetchall()}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE detection_records ADD COLUMN {column_name} {definition}")

    def save_record(self, record: Dict[str, Any]) -> None:
        batch_task_id = record.get("batch_task_id") or record["task_id"]
        batch_name = record.get("batch_name") or record["file_name"]
        batch_size = int(record.get("batch_size") or 1)
        batch_index = int(record.get("batch_index") or 1)

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO detection_records (
                        task_id, file_name, file_type, result_label, score,
                        source_path, result_json_path, preview_path, created_at,
                        model_version, inference_time, batch_task_id, batch_name,
                        batch_size, batch_index
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["task_id"],
                        record["file_name"],
                        record["file_type"],
                        record["result_label"],
                        float(record["score"]),
                        record["source_path"],
                        record["result_json_path"],
                        record.get("preview_path"),
                        record["created_at"],
                        record["model_version"],
                        float(record["inference_time"]),
                        batch_task_id,
                        batch_name,
                        batch_size,
                        batch_index,
                    ),
                )
                conn.commit()

    def list_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT
                    batch_task_id AS task_id,
                    MAX(batch_name) AS batch_name,
                    MAX(file_type) AS file_type,
                    COUNT(*) AS item_count,
                    SUM(CASE WHEN result_label = 'fake' THEN 1 ELSE 0 END) AS fake_count,
                    AVG(score) AS avg_score,
                    SUM(inference_time) AS total_inference_time,
                    MIN(created_at) AS created_at
                FROM detection_records
                GROUP BY batch_task_id
                ORDER BY MAX(id) DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_record(self, task_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM detection_records WHERE task_id = ? LIMIT 1",
                (task_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return dict(row)

    def get_batch_records(self, batch_task_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT *
                FROM detection_records
                WHERE batch_task_id = ?
                ORDER BY batch_index ASC, id ASC
                """,
                (batch_task_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def build_batch_summary(self, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not rows:
            return None

        first = rows[0]
        fake_count = sum(1 for row in rows if row["result_label"] == "fake")
        return {
            "task_id": first.get("batch_task_id") or first["task_id"],
            "batch_name": first.get("batch_name") or first["file_name"],
            "file_type": first["file_type"],
            "item_count": len(rows),
            "fake_count": fake_count,
            "avg_score": sum(float(row["score"]) for row in rows) / len(rows),
            "total_inference_time": sum(float(row["inference_time"]) for row in rows),
            "created_at": min(row["created_at"] for row in rows),
        }

    def load_result_json(self, result_json_path: str) -> Dict[str, Any]:
        with open(result_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

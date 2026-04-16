import json
import math
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
            items = [dict(row) for row in cur.fetchall()]
            for item in items:
                item_count = int(item.get("item_count") or 0)
                fake_count = int(item.get("fake_count") or 0)
                item["suspicious_rate"] = (fake_count / item_count) if item_count else 0.0
            return items

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
        item_count = len(rows)
        return {
            "task_id": first.get("batch_task_id") or first["task_id"],
            "batch_name": first.get("batch_name") or first["file_name"],
            "file_type": first["file_type"],
            "item_count": item_count,
            "fake_count": fake_count,
            "avg_score": sum(float(row["score"]) for row in rows) / len(rows),
            "total_inference_time": sum(float(row["inference_time"]) for row in rows),
            "created_at": min(row["created_at"] for row in rows),
            "suspicious_rate": (fake_count / item_count) if item_count else 0.0,
        }

    def get_history_summary(self, recent_limit: int = 20) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            overall = conn.execute(
                """
                SELECT
                    COUNT(DISTINCT batch_task_id) AS total_tasks,
                    COUNT(*) AS total_samples,
                    SUM(CASE WHEN result_label = 'fake' THEN 1 ELSE 0 END) AS total_fake_samples,
                    MAX(created_at) AS latest_created_at
                FROM detection_records
                """
            ).fetchone()

            recent_rows = conn.execute(
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
                (recent_limit,),
            ).fetchall()

            modality_rows = conn.execute(
                """
                SELECT
                    file_type,
                    COUNT(DISTINCT batch_task_id) AS batch_count,
                    COUNT(*) AS item_count,
                    SUM(CASE WHEN result_label = 'fake' THEN 1 ELSE 0 END) AS fake_count,
                    AVG(inference_time) AS avg_inference_time,
                    SUM(inference_time) AS total_inference_time
                FROM detection_records
                GROUP BY file_type
                ORDER BY file_type ASC
                """
            ).fetchall()

        total_tasks = int(overall["total_tasks"] or 0)
        total_samples = int(overall["total_samples"] or 0)
        total_fake_samples = int(overall["total_fake_samples"] or 0)
        overall_rate = (total_fake_samples / total_samples) if total_samples else 0.0

        recent_batches: List[Dict[str, Any]] = []
        for row in recent_rows:
            item_count = int(row["item_count"] or 0)
            fake_count = int(row["fake_count"] or 0)
            recent_batches.append(
                {
                    "task_id": row["task_id"],
                    "batch_name": row["batch_name"],
                    "file_type": row["file_type"],
                    "item_count": item_count,
                    "fake_count": fake_count,
                    "avg_score": float(row["avg_score"] or 0.0),
                    "total_inference_time": float(row["total_inference_time"] or 0.0),
                    "created_at": row["created_at"],
                    "suspicious_rate": (fake_count / item_count) if item_count else 0.0,
                }
            )

        recent_batches.reverse()
        for index, batch in enumerate(recent_batches, start=1):
            batch["short_label"] = f"#{index}"

        modalities: List[Dict[str, Any]] = []
        for row in modality_rows:
            item_count = int(row["item_count"] or 0)
            fake_count = int(row["fake_count"] or 0)
            modalities.append(
                {
                    "file_type": row["file_type"],
                    "batch_count": int(row["batch_count"] or 0),
                    "item_count": item_count,
                    "fake_count": fake_count,
                    "real_count": max(item_count - fake_count, 0),
                    "suspicious_rate": (fake_count / item_count) if item_count else 0.0,
                    "avg_inference_time": float(row["avg_inference_time"] or 0.0),
                    "total_inference_time": float(row["total_inference_time"] or 0.0),
                }
            )

        return {
            "total_tasks": total_tasks,
            "total_samples": total_samples,
            "total_fake_samples": total_fake_samples,
            "total_real_samples": max(total_samples - total_fake_samples, 0),
            "overall_suspicious_rate": overall_rate,
            "latest_created_at": overall["latest_created_at"],
            "recent_batches": recent_batches,
            "modalities": modalities,
        }

    def get_batch_analytics(self, batch_task_id: str, top_n: int = 5, bin_count: int = 10) -> Dict[str, Any]:
        rows = self.get_batch_records(batch_task_id)
        return self.build_batch_analytics(rows, top_n=top_n, bin_count=bin_count)

    def build_batch_analytics(
        self,
        rows: List[Dict[str, Any]],
        top_n: int = 5,
        bin_count: int = 10,
    ) -> Dict[str, Any]:
        if not rows:
            return {
                "item_count": 0,
                "fake_count": 0,
                "real_count": 0,
                "avg_score": 0.0,
                "suspicious_rate": 0.0,
                "verdict_share": [],
                "score_histogram": [],
                "top_risk_samples": [],
                "summary_text": "当前批次暂无可分析样本。",
            }

        normalized_rows = []
        for row in rows:
            normalized_rows.append(
                {
                    "task_id": row["task_id"],
                    "file_name": row["file_name"],
                    "label": row["result_label"],
                    "score": float(row["score"]),
                    "inference_time": float(row["inference_time"]),
                    "batch_index": int(row.get("batch_index") or 0),
                }
            )

        item_count = len(normalized_rows)
        fake_count = sum(1 for row in normalized_rows if row["label"] == "fake")
        real_count = item_count - fake_count
        avg_score = sum(row["score"] for row in normalized_rows) / item_count if item_count else 0.0
        suspicious_rate = (fake_count / item_count) if item_count else 0.0

        verdict_share = [
            {"name": "Fake", "label": "fake", "value": fake_count},
            {"name": "Real", "label": "real", "value": real_count},
        ]

        top_risk_samples = sorted(
            normalized_rows,
            key=lambda row: (-row["score"], row["batch_index"], row["file_name"]),
        )[:top_n]

        histogram = self._build_score_histogram([row["score"] for row in normalized_rows], bin_count=bin_count)

        summary_text = self._build_batch_conclusion(
            item_count=item_count,
            fake_count=fake_count,
            avg_score=avg_score,
            top_sample=top_risk_samples[0] if top_risk_samples else None,
        )

        return {
            "item_count": item_count,
            "fake_count": fake_count,
            "real_count": real_count,
            "avg_score": avg_score,
            "suspicious_rate": suspicious_rate,
            "verdict_share": verdict_share,
            "score_histogram": histogram,
            "top_risk_samples": top_risk_samples,
            "summary_text": summary_text,
        }

    def _build_score_histogram(self, scores: List[float], bin_count: int = 10) -> List[Dict[str, Any]]:
        if not scores or bin_count <= 0:
            return []

        counts = [0 for _ in range(bin_count)]
        for score in scores:
            clipped = min(max(float(score), 0.0), 0.999999)
            index = min(int(math.floor(clipped * bin_count)), bin_count - 1)
            counts[index] += 1

        histogram = []
        for index, count in enumerate(counts):
            start = index / bin_count
            end = (index + 1) / bin_count
            histogram.append(
                {
                    "label": f"{start:.1f}-{end:.1f}",
                    "count": count,
                    "start": start,
                    "end": end,
                }
            )
        return histogram

    def _build_batch_conclusion(
        self,
        item_count: int,
        fake_count: int,
        avg_score: float,
        top_sample: Optional[Dict[str, Any]],
    ) -> str:
        if item_count <= 0:
            return "当前批次暂无可分析样本。"

        suspicious_rate = fake_count / item_count
        if suspicious_rate >= 0.6 or avg_score >= 0.75:
            level = "整体风险偏高"
        elif suspicious_rate >= 0.25 or avg_score >= 0.55:
            level = "整体风险中等"
        elif fake_count > 0:
            level = "存在少量可疑样本"
        else:
            level = "整体结果偏稳定"

        summary = (
            f"当前批次共 {item_count} 个样本，其中 {fake_count} 个被判定为可疑，"
            f"可疑率 {suspicious_rate * 100:.1f}%，平均风险分 {avg_score:.3f}，{level}。"
        )
        if top_sample is not None:
            summary += (
                f" 最高风险样本为 {top_sample['file_name']}，"
                f"风险分 {float(top_sample['score']):.3f}。"
            )
        return summary

    def load_result_json(self, result_json_path: str) -> Dict[str, Any]:
        with open(result_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

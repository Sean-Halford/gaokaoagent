"""SQLite 数据库操作"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.storage.models import SubmissionRecord, EvaluationResult

logger = logging.getLogger(__name__)

from src.utils import get_project_root
PROJECT_ROOT = get_project_root()


def get_db_path() -> Path:
    """获取数据库路径"""
    db_dir = PROJECT_ROOT / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "submissions.db"


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """初始化数据库，创建表结构"""
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS submissions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path      TEXT NOT NULL,
            image_hash      TEXT DEFAULT '',
            timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
            question_type   TEXT NOT NULL,
            question_text   TEXT DEFAULT '',
            student_text    TEXT DEFAULT '',
            strengths       TEXT DEFAULT '[]',
            weaknesses      TEXT DEFAULT '[]',
            suggestions     TEXT DEFAULT '[]',
            mistake_tags    TEXT DEFAULT '[]',
            knowledge_gaps  TEXT DEFAULT '[]',
            full_report_md  TEXT DEFAULT '',
            reference_ids   TEXT DEFAULT '[]',
            model_used      TEXT DEFAULT '',
            tokens_used     INTEGER DEFAULT 0,
            is_mistake      BOOLEAN DEFAULT 1,
            is_reviewed     BOOLEAN DEFAULT 0,
            ocr_confidence  REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS knowledge_mastery (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_point  TEXT NOT NULL,
            question_type    TEXT NOT NULL,
            total_attempts   INTEGER DEFAULT 0,
            mistake_count    INTEGER DEFAULT 0,
            last_mistake_at  DATETIME,
            suggested_practice TEXT DEFAULT '',
            UNIQUE(knowledge_point, question_type)
        );

        CREATE TABLE IF NOT EXISTS practice_stats (
            date            DATE NOT NULL,
            question_type   TEXT NOT NULL,
            submissions     INTEGER DEFAULT 0,
            avg_score_ratio REAL DEFAULT 0.0,
            PRIMARY KEY (date, question_type)
        );
    """)

    conn.commit()
    logger.info(f"数据库初始化完成: {db_path}")
    return conn


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """获取数据库连接（自动初始化表）"""
    if db_path is None:
        db_path = get_db_path()
    if not Path(db_path).exists():
        return init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def insert_submission(record: SubmissionRecord,
                      db_path: str | Path | None = None
                      ) -> int:
    """插入一条提交记录，返回记录 ID"""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("""
            INSERT INTO submissions (
                image_path, image_hash, question_type, question_text,
                student_text,
                strengths, weaknesses, suggestions,
                mistake_tags, knowledge_gaps, full_report_md,
                reference_ids, model_used, tokens_used,
                is_mistake, is_reviewed, ocr_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.image_path,
            record.image_hash,
            record.question_type,
            record.question_text,
            record.student_text,
            record.strengths,
            record.weaknesses,
            record.suggestions,
            record.mistake_tags,
            record.knowledge_gaps,
            record.full_report_md,
            record.reference_ids,
            record.model_used,
            record.tokens_used,
            int(record.is_mistake),
            int(record.is_reviewed),
            record.ocr_confidence,
        ))
        conn.commit()
        record_id = cursor.lastrowid

        # 更新知识点掌握度
        _update_knowledge_mastery(conn, record)

        # 更新统计
        _update_practice_stats(conn, record)

        logger.info(f"提交记录已保存: id={record_id}")
        return record_id
    finally:
        conn.close()


def _update_knowledge_mastery(conn: sqlite3.Connection,
                              record: SubmissionRecord):
    """更新知识点掌握度追踪"""
    gaps = json.loads(record.knowledge_gaps) if record.knowledge_gaps else []
    tags = json.loads(record.mistake_tags) if record.mistake_tags else []
    all_points = gaps + tags

    for point in all_points:
        conn.execute("""
            INSERT INTO knowledge_mastery
                (knowledge_point, question_type, total_attempts, mistake_count, last_mistake_at)
            VALUES (?, ?, 1, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(knowledge_point, question_type) DO UPDATE SET
                total_attempts = total_attempts + 1,
                mistake_count = mistake_count + 1,
                last_mistake_at = CURRENT_TIMESTAMP
        """, (point, record.question_type))


def _update_practice_stats(conn: sqlite3.Connection,
                           record: SubmissionRecord):
    """更新每日练习统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("""
        INSERT INTO practice_stats (date, question_type, submissions)
        VALUES (?, ?, 1)
        ON CONFLICT(date, question_type) DO UPDATE SET
            submissions = submissions + 1
    """, (today, record.question_type))


def get_submission(submission_id: int,
                   db_path: str | Path | None = None
                   ) -> Optional[SubmissionRecord]:
    """获取单条提交记录"""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (submission_id,)
        ).fetchone()
        if row is None:
            return None
        return SubmissionRecord(**dict(row))
    finally:
        conn.close()


def list_submissions(question_type: str | None = None,
                     limit: int = 50,
                     offset: int = 0,
                     db_path: str | Path | None = None
                     ) -> list[SubmissionRecord]:
    """列出提交记录，可按题型筛选"""
    conn = get_connection(db_path)
    try:
        if question_type:
            rows = conn.execute(
                "SELECT * FROM submissions WHERE question_type = ? "
                "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (question_type, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM submissions "
                "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [SubmissionRecord(**dict(r)) for r in rows]
    finally:
        conn.close()


def get_mistakes(question_type: str | None = None,
                 limit: int = 100,
                 db_path: str | Path | None = None
                 ) -> list[SubmissionRecord]:
    """获取错题列表"""
    conn = get_connection(db_path)
    try:
        if question_type:
            rows = conn.execute(
                "SELECT * FROM submissions "
                "WHERE is_mistake = 1 AND question_type = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (question_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM submissions "
                "WHERE is_mistake = 1 "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [SubmissionRecord(**dict(r)) for r in rows]
    finally:
        conn.close()


def get_knowledge_stats(db_path: str | Path | None = None
                        ) -> list[dict]:
    """获取知识点掌握度统计"""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM knowledge_mastery "
            "ORDER BY mistake_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_practice_stats(days: int = 30,
                       db_path: str | Path | None = None
                       ) -> list[dict]:
    """获取最近 N 天的练习统计"""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM practice_stats "
            "ORDER BY date DESC LIMIT ?",
            (days * 7,)  # 最多 7 种题型/天
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_reviewed(submission_id: int,
                  db_path: str | Path | None = None):
    """标记为已复习"""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE submissions SET is_reviewed = 1 WHERE id = ?",
            (submission_id,)
        )
        conn.commit()
    finally:
        conn.close()

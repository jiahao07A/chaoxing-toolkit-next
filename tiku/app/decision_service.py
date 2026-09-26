"""统一答题决策、匹配解释和本地旁路审计。"""

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .answer_service import AnswerService
from .matching import combined_score, normalize_question, options_match_score, text_similarity
from .schemas import DecisionCandidateSummary, DecisionRequest, DecisionResult

AUDIT_RETENTION_DAYS = 7
MAX_CANDIDATE_SUMMARIES = 5


def digest(value: str) -> str:
    """返回固定长度摘要，避免审计记录保存题目或答案原文。"""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def normalized_question_preview(value: str) -> str:
    """保留规范化题干的长度和空格结构，但不落原始文字。"""
    normalized = normalize_question(value)
    return "".join(" " if char.isspace() else "•" for char in normalized)


class DecisionService:
    """把现有本地题库能力包成统一决策边界，旁路只落脱敏摘要。"""

    def __init__(self, db):
        self.db = db

    async def ensure_audit_table(self):
        conn = await self.db._get_connection()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_digest TEXT NOT NULL,
                    question_digest TEXT NOT NULL,
                    normalized_question_preview TEXT NOT NULL DEFAULT '',
                    question_type TEXT NOT NULL DEFAULT '',
                    option_count INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    match_stage TEXT NOT NULL DEFAULT 'unknown',
                    status TEXT NOT NULL,
                    found INTEGER NOT NULL,
                    candidate_count INTEGER NOT NULL DEFAULT 0,
                    candidate_summaries TEXT NOT NULL DEFAULT '[]',
                    failure_reason TEXT,
                    answer_digest TEXT,
                    duration_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            cursor = await conn.execute("PRAGMA table_info(decision_audits)")
            existing = {row["name"] for row in await cursor.fetchall()}
            migrations = {
                "question_type": "TEXT NOT NULL DEFAULT ''",
                "normalized_question_preview": "TEXT NOT NULL DEFAULT ''",
                "option_count": "INTEGER NOT NULL DEFAULT 0",
                "match_stage": "TEXT NOT NULL DEFAULT 'unknown'",
                "candidate_count": "INTEGER NOT NULL DEFAULT 0",
                "candidate_summaries": "TEXT NOT NULL DEFAULT '[]'",
                "failure_reason": "TEXT",
            }
            for column, definition in migrations.items():
                if column not in existing:
                    await conn.execute(
                        f"ALTER TABLE decision_audits ADD COLUMN {column} {definition}"
                    )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decision_audits_created "
                "ON decision_audits(created_at)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decision_audits_stage "
                "ON decision_audits(match_stage)"
            )
            await conn.commit()
        finally:
            await self.db._release_connection(conn)

    async def _trace_match(self, request: DecisionRequest) -> dict[str, Any]:
        """复用本地匹配规则生成只读解释，不修改题库或待处理队列。"""

        question = request.question.replace("'", "").replace('"', "")
        has_options = bool(request.options)
        candidates: list[tuple[float, dict, str]] = []
        conn = await self.db._get_connection()
        try:
            async def append_rows(rows, score: float, stage: str):
                for row in rows:
                    candidates.append((score, self.db._row_to_dict(row), stage))

            async def fetch_one(sql: str, params: tuple):
                cursor = await conn.execute(sql, params)
                row = await cursor.fetchone()
                return [row] if row else []

            if request.question_type:
                rows = await fetch_one(
                    "SELECT * FROM questions WHERE question = ? AND type = ?",
                    (question, request.question_type),
                )
                if rows:
                    await append_rows(rows, 1.0, "exact_typed")
                else:
                    cursor = await conn.execute(
                        "SELECT * FROM questions WHERE question LIKE ? AND type = ? LIMIT 10",
                        (f"%{question[:100]}%", request.question_type),
                    )
                    await append_rows(await cursor.fetchall(), 0.9, "contains_typed")

            if not candidates:
                rows = await fetch_one(
                    "SELECT * FROM questions WHERE question = ?", (question,)
                )
                await append_rows(rows, 1.0, "exact")

            if not candidates:
                cursor = await conn.execute(
                    "SELECT * FROM questions WHERE question LIKE ? LIMIT 10",
                    (f"%{question[:100]}%",),
                )
                await append_rows(await cursor.fetchall(), 0.85, "contains")

            if not candidates:
                cursor = await conn.execute(
                    "SELECT * FROM questions WHERE ? LIKE '%' || question || '%' LIMIT 10",
                    (question[:50],),
                )
                await append_rows(await cursor.fetchall(), 0.8, "reverse_contains")

            if not candidates:
                clean_text = question.strip().rstrip(")").rstrip(" ").rstrip("(").rstrip(" ")
                if clean_text and clean_text != question and len(clean_text) > 5:
                    cursor = await conn.execute(
                        "SELECT * FROM questions WHERE question LIKE ? LIMIT 10",
                        (f"%{clean_text[:100]}%",),
                    )
                    await append_rows(await cursor.fetchall(), 0.75, "trimmed_contains")

            if not candidates:
                no_underscore = question.replace("_", "").strip()
                if no_underscore and no_underscore != question and len(no_underscore) > 5:
                    cursor = await conn.execute(
                        "SELECT * FROM questions WHERE question LIKE ? OR ? LIKE '%' || question || '%' LIMIT 10",
                        (f"%{no_underscore[:100]}%", no_underscore[:100]),
                    )
                    await append_rows(await cursor.fetchall(), 0.7, "underscore_normalized")

            if not candidates:
                normalized_input = normalize_question(question)
                if normalized_input and len(normalized_input) > 5:
                    input_len = len(normalized_input)
                    cursor = await conn.execute(
                        "SELECT * FROM questions WHERE length(question) >= ? "
                        "AND length(question) <= ? LIMIT 500",
                        (max(1, input_len - 20), input_len + 20),
                    )
                    for row in await cursor.fetchall():
                        item = self.db._row_to_dict(row)
                        score = text_similarity(normalized_input, normalize_question(item["question"]))
                        if score >= 0.85:
                            candidates.append((score, item, "normalized_similarity"))

            scored: list[tuple[float, float, dict, str]] = []
            if has_options:
                for text_score, candidate, stage in candidates:
                    option_score = options_match_score(request.options, candidate.get("options", []))
                    scored.append((combined_score(text_score, option_score, True), option_score, candidate, stage))
                scored.sort(key=lambda item: item[0], reverse=True)
                if any(candidate.get("options") for _, _, candidate, _ in scored):
                    scored = [item for item in scored if item[2].get("options")]
                    scored = [item for item in scored if item[1] > 0]
            else:
                scored = [(text_score, 0.0, candidate, stage) for text_score, candidate, stage in candidates]

            selected = scored[0][2] if scored and scored[0][0] > 0.3 else None
            if selected:
                failure_reason = None
            elif not candidates:
                failure_reason = "no_candidate"
            elif has_options and not scored:
                failure_reason = "options_mismatch"
            else:
                failure_reason = "score_below_threshold"

            summaries: list[DecisionCandidateSummary] = []
            for rank, (score, option_score, candidate, _stage) in enumerate(scored[:MAX_CANDIDATE_SUMMARIES], 1):
                text_score = score if not has_options else (score - option_score * 0.3) / 0.7
                summaries.append(
                    DecisionCandidateSummary(
                        id=candidate.get("id"),
                        question_digest=digest(candidate.get("question", "")),
                        type=str(candidate.get("type", "")),
                        rank=rank,
                        text_score=round(max(0.0, min(1.0, text_score)), 4),
                        options_score=round(max(0.0, min(1.0, option_score)), 4),
                        score=round(max(0.0, min(1.0, score)), 4),
                        answer_digest=digest(str(candidate.get("answer", ""))) if candidate.get("answer") else None,
                    )
                )

            return {
                "match_stage": scored[0][3] if scored else (candidates[0][2] if candidates else "none"),
                "failure_reason": failure_reason,
                "candidates": summaries,
            }
        finally:
            await self.db._release_connection(conn)

    async def search(self, question: str, question_type: str, options=None) -> dict[str, Any]:
        started = time.perf_counter()
        request = DecisionRequest(
            question=question,
            question_type=question_type,
            options=list(options or []),
        )
        # 正式结果仍由原有 AnswerService 决定；解释仅作为旁路数据。
        result = await AnswerService(self.db).search(
            request.question, request.question_type, request.options
        )
        try:
            trace = await self._trace_match(request)
        except Exception:
            # 解释是旁路能力，任何诊断失败都不能影响正式答案。
            trace = {
                "match_stage": "unknown",
                "failure_reason": "audit_trace_failed",
                "candidates": [],
            }
        duration_ms = max(0, round((time.perf_counter() - started) * 1000))
        decision = DecisionResult(
            found=bool(result.get("found")),
            answer=str(result.get("answer") or ""),
            source=str(result.get("source") or "local"),
            status=str(result.get("status") or "unknown"),
            stage=str(result.get("stage") or "local"),
            match_stage=trace["match_stage"],
            failure_reason=trace["failure_reason"] if not result.get("found") else None,
            candidates=trace["candidates"],
        )
        summary = {
            **result,
            "question_digest": digest(request.question),
            "request_digest": digest(
                json.dumps(
                    {
                        "question": request.question,
                        "type": request.question_type,
                        "options": request.options,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            ),
            "question_type": request.question_type,
            "normalized_question_preview": normalized_question_preview(request.question),
            "option_count": len(request.options),
            "match_stage": decision.match_stage,
            "failure_reason": decision.failure_reason,
            "candidates": [candidate.model_dump() for candidate in decision.candidates],
            "duration_ms": duration_ms,
        }
        try:
            await self.record(summary)
        except Exception:
            # 旁路记录不能阻断正式答题结果。
            pass
        return result

    async def record(self, summary: dict[str, Any]) -> None:
        await self.ensure_audit_table()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=AUDIT_RETENTION_DAYS)
        conn = await self.db._get_connection()
        try:
            await conn.execute(
                """INSERT INTO decision_audits
                (request_digest, question_digest, normalized_question_preview, question_type, option_count,
                 source, stage, match_stage, status, found, candidate_count,
                 candidate_summaries, failure_reason, answer_digest, duration_ms,
                 created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary["request_digest"],
                    summary["question_digest"],
                    summary.get("normalized_question_preview", ""),
                    summary.get("question_type", ""),
                    summary.get("option_count", 0),
                    summary["source"],
                    summary["stage"],
                    summary.get("match_stage", "unknown"),
                    summary["status"],
                    int(summary["found"]),
                    len(summary.get("candidates", [])),
                    json.dumps(summary.get("candidates", []), ensure_ascii=False),
                    summary.get("failure_reason"),
                    digest(summary["answer"]) if summary.get("answer") else None,
                    summary["duration_ms"],
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
            await conn.execute(
                "DELETE FROM decision_audits WHERE expires_at <= ?", (now.isoformat(),)
            )
            await conn.commit()
        finally:
            await self.db._release_connection(conn)

    async def cleanup_expired_audits(self) -> int:
        """删除超过七天的审计摘要，返回删除数量。"""

        await self.ensure_audit_table()
        conn = await self.db._get_connection()
        try:
            cursor = await conn.execute(
                "DELETE FROM decision_audits WHERE expires_at <= ?",
                (datetime.now(timezone.utc).isoformat(),),
            )
            await conn.commit()
            return cursor.rowcount
        finally:
            await self.db._release_connection(conn)

    @staticmethod
    def _decode_audit(row: dict[str, Any]) -> dict[str, Any]:
        value = row.get("candidate_summaries") or "[]"
        try:
            row["candidate_summaries"] = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            row["candidate_summaries"] = []
        return row

    async def list_audits(self, limit: int = 100, request_digest: str | None = None) -> list[dict[str, Any]]:
        await self.ensure_audit_table()
        conn = await self.db._get_connection()
        try:
            columns = (
                "id, request_digest, question_digest, normalized_question_preview, question_type, option_count, "
                "source, stage, match_stage, status, found, candidate_count, "
                "candidate_summaries, failure_reason, answer_digest, duration_ms, created_at"
            )
            if request_digest:
                cursor = await conn.execute(
                    f"SELECT {columns} FROM decision_audits WHERE request_digest = ? "
                    "AND expires_at > ? ORDER BY id DESC LIMIT ?",
                    (request_digest, datetime.now(timezone.utc).isoformat(), limit),
                )
            else:
                cursor = await conn.execute(
                    f"SELECT {columns} FROM decision_audits WHERE expires_at > ? "
                    "ORDER BY id DESC LIMIT ?",
                    (datetime.now(timezone.utc).isoformat(), limit),
                )
            return [self._decode_audit(dict(row)) for row in await cursor.fetchall()]
        finally:
            await self.db._release_connection(conn)

    async def list_match_quality(
        self,
        page: int = 1,
        page_size: int = 20,
        match_stage: str | None = None,
        status: str | None = None,
        found: bool | None = None,
    ) -> dict[str, Any]:
        """只读质量工作台查询，按七天有效期过滤，不在查询中修改数据库。"""

        page = max(1, page)
        page_size = max(1, min(100, page_size))
        where = ["expires_at > ?"]
        params: list[Any] = [datetime.now(timezone.utc).isoformat()]
        if match_stage:
            where.append("match_stage = ?")
            params.append(match_stage)
        if status:
            where.append("status = ?")
            params.append(status)
        if found is not None:
            where.append("found = ?")
            params.append(int(found))
        clause = " AND ".join(where)
        conn = await self.db._get_connection()
        try:
            total_cursor = await conn.execute(
                f"SELECT COUNT(*) FROM decision_audits WHERE {clause}", params
            )
            total = int((await total_cursor.fetchone())[0])
            offset = (page - 1) * page_size
            cursor = await conn.execute(
                "SELECT id, request_digest, question_digest, normalized_question_preview, question_type, option_count, "
                "source, stage, match_stage, status, found, candidate_count, "
                "candidate_summaries, failure_reason, answer_digest, duration_ms, created_at "
                f"FROM decision_audits WHERE {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            )
            items = [self._decode_audit(dict(row)) for row in await cursor.fetchall()]
            summary_cursor = await conn.execute(
                f"SELECT match_stage, status, found, COUNT(*) AS count "
                f"FROM decision_audits WHERE {clause} GROUP BY match_stage, status, found",
                params,
            )
            summary = [dict(row) for row in await summary_cursor.fetchall()]
            return {"page": page, "page_size": page_size, "total": total, "items": items, "summary": summary}
        finally:
            await self.db._release_connection(conn)

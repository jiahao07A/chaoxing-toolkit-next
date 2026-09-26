"""题库 JSON 导入预检、事务提交与题库专用备份。"""

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import MAX_OPTIONS_COUNT, MAX_QUESTION_LENGTH
from .database import AsyncDatabase

logger = logging.getLogger(__name__)
BACKUP_LIMIT = 5
PREVIEW_TTL_MINUTES = 60


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _merge_key(question: str, question_type: str, options: list[str]) -> str:
    value = [_normalize(question), question_type.strip(), [_normalize(option) for option in options]]
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class ImportService:
    def __init__(self, db: AsyncDatabase, backup_dir: str | Path):
        self.db = db
        self.backup_dir = Path(backup_dir)

    async def _ensure_tables(self, conn):
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS import_runs (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT,
                report_json TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS import_backups (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                source_run_id TEXT NOT NULL
            )
        """)

    async def preview(self, content: bytes, source_name: str) -> dict[str, Any]:
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("文件超过 10MB")
        try:
            rows = json.loads(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise ValueError("文件编码错误，请使用 UTF-8 编码") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON 解析失败：{exc.msg}") from exc
        if not isinstance(rows, list):
            raise ValueError("JSON 根元素必须是数组")

        errors: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        accepted: dict[str, tuple[dict[str, Any], int]] = {}
        repeated: set[str] = set()
        for index, item in enumerate(rows, start=1):
            if not isinstance(item, dict):
                errors.append({"line": index, "code": "invalid_record", "message": "题目必须是对象"})
                continue
            question = item.get("question")
            question_type = item.get("type")
            answer = item.get("answer")
            options = item.get("options", [])
            reason = None
            if not isinstance(question, str) or not question.strip():
                reason = ("missing_question", "题干不能为空")
            elif len(question) > MAX_QUESTION_LENGTH:
                reason = ("question_too_long", "题干超过长度限制")
            elif isinstance(question_type, bool) or not isinstance(question_type, (str, int)) or not str(question_type).strip():
                reason = ("missing_type", "题型不能为空")
            elif not isinstance(answer, str) or not answer.strip():
                reason = ("missing_answer", "答案不能为空")
            elif len(str(question_type)) > 50:
                reason = ("type_too_long", "题型超过长度限制")
            elif len(answer) > 1000:
                reason = ("answer_too_long", "答案超过长度限制")
            elif not isinstance(options, list) or len(options) > MAX_OPTIONS_COUNT or any(not isinstance(option, str) for option in options):
                reason = ("invalid_options", "选项必须是字符串数组且不能超过数量限制")
            elif any(len(option) > 500 for option in options):
                reason = ("option_too_long", "单个选项超过长度限制")
            if reason:
                errors.append({"line": index, "code": reason[0], "message": reason[1]})
                continue

            record = {
                "question": question.strip(),
                "type": str(question_type).strip(),
                "options": options,
                "answer": answer.strip(),
            }
            key = _merge_key(record["question"], record["type"], record["options"])
            if key in accepted:
                first_record, first_line = accepted[key]
                repeated.add(key)
                if first_record["answer"] != record["answer"]:
                    conflicts.append({
                        "line": index,
                        "other_line": first_line,
                        "code": "file_answer_conflict",
                        "message": "同一规范化题目对应了不同答案",
                    })
                continue
            accepted[key] = (record, index)

        conn = await self.db._get_connection()
        try:
            await self._ensure_tables(conn)
            cursor = await conn.execute("SELECT id, question, type, options, answer FROM questions")
            existing_rows = await cursor.fetchall()
            existing: dict[str, list[dict[str, Any]]] = {}
            for row in existing_rows:
                try:
                    options = json.loads(row["options"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    options = []
                key = _merge_key(row["question"], row["type"], options)
                existing.setdefault(key, []).append({
                    "id": row["id"],
                    "question": row["question"],
                    "type": row["type"],
                    "options": options,
                    "answer": row["answer"],
                })

            new_count = 0
            updated_count = 0
            skipped_count = len(repeated)
            for key, (record, line) in accepted.items():
                matches = existing.get(key, [])
                if len(matches) > 1:
                    conflicts.append({"line": line, "code": "ambiguous_existing_match", "message": "现有题库中存在多条规范化后相同的题目"})
                elif matches and matches[0]["answer"] != record["answer"]:
                    conflicts.append({"line": line, "code": "existing_answer_conflict", "message": "导入答案与现有题库答案不一致"})
                elif matches:
                    existing_record = matches[0]
                    if any(existing_record[field] != record[field] for field in ("question", "type", "options", "answer")):
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    new_count += 1

            report = {
                "source": source_name,
                "total": len(rows),
                "valid": len(accepted),
                "new": new_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": errors,
                "conflicts": conflicts,
                "can_commit": (new_count > 0 or updated_count > 0) and not errors and not conflicts,
            }
            run_id = str(uuid.uuid4())
            payload = {
                "records": [record for record, _ in accepted.values()],
                "new_keys": [key for key in accepted if key not in existing],
                "existing_snapshots": {
                    key: existing[key] for key in accepted if key in existing
                },
            }
            await conn.execute("DELETE FROM import_runs WHERE status = 'previewed' AND created_at < datetime('now', ?)", (f"-{PREVIEW_TTL_MINUTES} minutes",))
            await conn.execute(
                "INSERT INTO import_runs (id, source_name, source_sha256, created_at, status, payload_json, report_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, source_name[:255], hashlib.sha256(content).hexdigest(), datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"), "previewed", json.dumps(payload, ensure_ascii=False), json.dumps(report, ensure_ascii=False)),
            )
            await conn.commit()
            return {"run_id": run_id, **report}
        except Exception:
            await conn.rollback()
            raise
        finally:
            await self.db._release_connection(conn)

    async def _make_backup(self, conn, run_id: str) -> dict[str, Any]:
        cursor = await conn.execute("SELECT * FROM questions ORDER BY id")
        rows = [dict(row) for row in await cursor.fetchall()]
        backup_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        payload = json.dumps({"version": 1, "questions": rows}, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{created_at[:10]}-{backup_id}.json"
        path = self.backup_dir / file_name
        path.write_text(payload, encoding="utf-8")
        try:
            await conn.execute(
                "INSERT INTO import_backups (id, file_name, created_at, row_count, sha256, source_run_id) VALUES (?, ?, ?, ?, ?, ?)",
                (backup_id, file_name, created_at, len(rows), digest, run_id),
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {"id": backup_id, "file_name": file_name, "created_at": created_at, "row_count": len(rows), "sha256": digest}

    async def commit(self, run_id: str) -> dict[str, Any]:
        async with self.db._write_lock:
            conn = await self.db._get_connection()
            backup_path: Path | None = None
            try:
                await self._ensure_tables(conn)
                await conn.execute("BEGIN IMMEDIATE")
                cursor = await conn.execute("SELECT * FROM import_runs WHERE id = ?", (run_id,))
                run = await cursor.fetchone()
                if not run or run["status"] != "previewed" or not run["payload_json"]:
                    raise ValueError("预检记录不存在、已处理或已过期，请重新预检")
                report = json.loads(run["report_json"])
                if not report.get("can_commit"):
                    raise ValueError("预检包含错误或冲突，不能提交")

                payload = json.loads(run["payload_json"])
                records = payload["records"]
                new_keys = set(payload["new_keys"])
                expected_snapshots = payload.get("existing_snapshots", {})
                cursor = await conn.execute("SELECT id, question, type, options, answer FROM questions")
                current_snapshots: dict[str, list[dict[str, Any]]] = {}
                for row in await cursor.fetchall():
                    try:
                        existing_options = json.loads(row["options"] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        existing_options = []
                    key = _merge_key(row["question"], row["type"], existing_options)
                    current_snapshots.setdefault(key, []).append({
                        "id": row["id"],
                        "question": row["question"],
                        "type": row["type"],
                        "options": existing_options,
                        "answer": row["answer"],
                    })
                keys = {_merge_key(q["question"], q["type"], q["options"]) for q in records}
                if any(current_snapshots.get(key, []) != expected_snapshots.get(key, []) for key in keys):
                    raise ValueError("题库在预检后发生变化，请重新预检")

                questions = [
                    question for question in records
                    if _merge_key(question["question"], question["type"], question["options"]) in new_keys
                ]
                updates = []
                for question in records:
                    key = _merge_key(question["question"], question["type"], question["options"])
                    matches = expected_snapshots.get(key, [])
                    if len(matches) == 1 and any(matches[0][field] != question[field] for field in ("question", "type", "options", "answer")):
                        updates.append((matches[0]["id"], question))
                backup = await self._make_backup(conn, run_id)
                backup_path = self.backup_dir / backup["file_name"]
                for question in questions:
                    await conn.execute(
                        "INSERT INTO questions (question, type, options, answer) VALUES (?, ?, ?, ?)",
                        (question["question"], question["type"], json.dumps(question["options"], ensure_ascii=False), question["answer"]),
                    )
                for question_id, question in updates:
                    await conn.execute(
                        "UPDATE questions SET question = ?, type = ?, options = ?, answer = ? WHERE id = ?",
                        (question["question"], question["type"], json.dumps(question["options"], ensure_ascii=False), question["answer"], question_id),
                    )
                await conn.execute("UPDATE import_runs SET status = 'committed', payload_json = NULL WHERE id = ?", (run_id,))
                await conn.commit()
                self.db._question_count = None
                try:
                    await self._prune_backups(conn)
                except Exception:
                    logger.exception("清理过期题库备份失败，已保留本次导入结果")
                return {"run_id": run_id, "added": len(questions), "updated": len(updates), "skipped": report["skipped"], "backup": backup}
            except ValueError:
                await conn.rollback()
                raise
            except Exception:
                await conn.rollback()
                if backup_path and backup_path.exists():
                    backup_path.unlink()
                raise
            finally:
                await self.db._release_connection(conn)

    async def _prune_backups(self, conn):
        cursor = await conn.execute("SELECT id, file_name FROM import_backups ORDER BY created_at DESC, id DESC")
        backups = await cursor.fetchall()
        for backup in backups[BACKUP_LIMIT:]:
            path = self.backup_dir / backup["file_name"]
            if path.parent.resolve() == self.backup_dir.resolve() and path.exists():
                path.unlink()
            await conn.execute("DELETE FROM import_backups WHERE id = ?", (backup["id"],))
        await conn.commit()

    async def list_backups(self) -> list[dict[str, Any]]:
        conn = await self.db._get_connection()
        try:
            await self._ensure_tables(conn)
            cursor = await conn.execute("SELECT id, created_at, row_count, sha256 FROM import_backups ORDER BY created_at DESC, id DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            await self.db._release_connection(conn)

    async def restore(self, backup_id: str) -> dict[str, Any]:
        async with self.db._write_lock:
            conn = await self.db._get_connection()
            try:
                await self._ensure_tables(conn)
                cursor = await conn.execute("SELECT * FROM import_backups WHERE id = ?", (backup_id,))
                backup = await cursor.fetchone()
                if not backup:
                    raise ValueError("备份不存在")
                path = self.backup_dir / backup["file_name"]
                if path.parent.resolve() != self.backup_dir.resolve() or not path.is_file():
                    raise ValueError("备份文件不存在或路径无效")
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != backup["sha256"]:
                    raise ValueError("备份校验失败，文件可能已损坏")
                snapshot = json.loads(content)
                questions = snapshot.get("questions") if isinstance(snapshot, dict) and snapshot.get("version") == 1 else None
                if not isinstance(questions, list):
                    raise ValueError("备份格式无效")

                await conn.execute("BEGIN IMMEDIATE")
                await conn.execute("DELETE FROM questions")
                for item in questions:
                    await conn.execute(
                        "INSERT INTO questions (id, question, type, options, answer, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (item["id"], item["question"], item["type"], item["options"], item["answer"], item["created_at"]),
                    )
                await conn.commit()
                self.db._question_count = None
                return {"restored": len(questions), "backup_id": backup_id}
            except ValueError:
                await conn.rollback()
                raise
            except Exception:
                await conn.rollback()
                raise
            finally:
                await self.db._release_connection(conn)

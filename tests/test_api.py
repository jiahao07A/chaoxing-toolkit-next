import pytest
import hashlib
import json
from pathlib import Path
from httpx import ASGITransport, AsyncClient


def test_config_contract_hash_is_embedded_in_userscript():
    schema_path = Path("config/settings.schema.json")
    script_path = Path("scripts/userscript/学习通脚本.js")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    canonical = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    script = script_path.read_text(encoding="utf-8")
    assert source_hash in script
    assert "validateGeneratedConfigContract" in script
    assert "return false" in script
    assert "normalizedConfig" in script
    for key, spec in schema["properties"].items():
        assert key in script
        assert json.dumps(spec["default"], ensure_ascii=False) in script


@pytest.mark.anyio
async def test_stats_api_uses_isolated_database(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/stats")

    assert response.status_code == 200
    assert response.json() == {"code": 1, "data": {"total": 0, "pending": 0}}


@pytest.mark.anyio
async def test_config_contract_fills_random_pause_defaults_for_legacy_config(isolated_app):
    app = isolated_app
    Path(app.state.config_file).write_text(
        '{"version": 7, "config": {"autoVideo": false}}', encoding="utf-8"
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/config")

    config = response.json()["data"]
    assert config["version"] == 7
    assert config["config"]["autoVideo"] is False
    assert config["config"]["randomPauseEnabled"] is False
    assert config["config"]["randomPauseIntervalMin"] == 30
    assert config["config"]["randomPauseIntervalMax"] == 93
    assert config["config"]["randomPauseDurationMin"] == 2
    assert config["config"]["randomPauseDurationMax"] == 5


@pytest.mark.anyio
async def test_config_defaults_api_returns_the_server_default_contract(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/config/defaults")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 1
    assert body["data"]["config"]["autoVideo"] is True
    assert body["data"]["config"]["randomPauseIntervalMin"] == 30
    assert body["data"]["config"]["thtoken"] == ""


@pytest.mark.anyio
async def test_config_contract_rejects_random_pause_out_of_range_and_reversed_bounds(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            too_large = await client.put(
                "/api/config",
                json={"config": {"randomPauseIntervalMax": 86401}},
            )
            not_integer = await client.put(
                "/api/config",
                json={"config": {"randomPauseDurationMin": "2"}},
            )
            reversed_bounds = await client.put(
                "/api/config",
                json={
                    "config": {
                        "randomPauseIntervalMin": 90,
                        "randomPauseIntervalMax": 30,
                    }
                },
            )

    assert too_large.status_code == 422
    assert not_integer.status_code == 422
    assert reversed_bounds.status_code == 422


@pytest.mark.anyio
async def test_health_reports_ready_state_and_restricts_cors_to_localhost(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            health = await client.get("/api/health")
            local = await client.get("/api/stats", headers={"Origin": "http://localhost:8002"})
            remote = await client.get("/api/stats", headers={"Origin": "https://example.com"})

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["database"] is True
    assert health.json()["config"] is True
    assert local.headers.get("access-control-allow-origin") == "http://localhost:8002"
    assert "access-control-allow-origin" not in remote.headers


@pytest.mark.anyio
async def test_health_reports_service_database_and_config_and_restricts_cors(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            health = await client.get(
                "/api/health",
                headers={"Origin": "http://localhost:8002"},
            )
            foreign = await client.get(
                "/api/health",
                headers={"Origin": "https://example.invalid"},
            )

    body = health.json()
    assert health.status_code == 200
    assert body["status"] == "ok"
    assert body["service"]["name"] == "tiku"
    assert body["service"]["status"] == "ok"
    assert body["database"] is True
    assert body["database_detail"]["status"] == "ok"
    assert body["config"] is True
    assert body["config_detail"]["status"] == "ok"
    assert health.headers["access-control-allow-origin"] == "http://localhost:8002"
    assert "access-control-allow-origin" not in foreign.headers


@pytest.mark.anyio
async def test_question_api_round_trip_uses_test_database(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            create_response = await client.post(
                "/api/questions",
                json={
                    "question": "测试题目",
                    "type": "0",
                    "options": ["选项 A"],
                    "answer": "选项 A",
                },
            )
            list_response = await client.get("/api/questions", params={"limit": 20})

    assert create_response.status_code == 200
    assert create_response.json()["data"]["id"] == 1
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["data"][0]["question"] == "测试题目"


@pytest.mark.anyio
async def test_import_preview_commit_and_restore_leave_pending_questions_unchanged(isolated_app):
    app = isolated_app
    content = '[{"question":"题干 A","type":"0","options":["选项 A"],"answer":"答案"}]'.encode("utf-8")
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/search", json={"question": "未命中题目", "type": "0"})
            preview_response = await client.post(
                "/api/import-json/preview",
                files={"file": ("questions.json", content, "application/json")},
            )
            before_commit = await client.get("/api/stats")
            commit_response = await client.post(
                "/api/import-json/commit",
                json={"run_id": preview_response.json()["data"]["run_id"]},
            )
            second_preview = await client.post(
                "/api/import-json/preview",
                files={
                    "file": (
                        "second.json",
                        '[{"question":"第二道题","type":"0","options":[],"answer":"答案"}]',
                        "application/json",
                    )
                },
            )
            second_commit = await client.post(
                "/api/import-json/commit",
                json={"run_id": second_preview.json()["data"]["run_id"]},
            )
            backups = await client.get("/api/import-backups")
            restore_response = await client.post(
                f"/api/import-backups/{backups.json()['data'][-1]['id']}/restore"
            )
            after_restore = await client.get("/api/stats")
            pending = await client.get("/api/pending")

    assert preview_response.status_code == 200
    assert preview_response.json()["data"]["can_commit"] is True
    assert preview_response.json()["data"]["new"] == 1
    assert before_commit.json()["data"] == {"total": 0, "pending": 1}
    assert commit_response.json()["data"]["added"] == 1
    assert second_commit.json()["data"]["added"] == 1
    assert backups.json()["data"][-1]["row_count"] == 0
    assert restore_response.status_code == 200
    assert after_restore.json()["data"] == {"total": 0, "pending": 1}
    assert len(pending.json()["data"]) == 1


@pytest.mark.anyio
async def test_import_keeps_only_five_recent_backups(isolated_app, tmp_path):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for number in range(6):
                preview = await client.post(
                    "/api/import-json/preview",
                    files={
                        "file": (
                            f"{number}.json",
                            f'[{{"question":"题目 {number}","type":"0","options":[],"answer":"答案"}}]',
                            "application/json",
                        )
                    },
                )
                assert preview.status_code == 200
                result = await client.post(
                    "/api/import-json/commit",
                    json={"run_id": preview.json()["data"]["run_id"]},
                )
                assert result.status_code == 200
            backups = await client.get("/api/import-backups")

    assert len(backups.json()["data"]) == 5
    assert len(list((tmp_path / "import_backups").glob("*.json"))) == 5


@pytest.mark.anyio
async def test_import_conflicts_block_submission_and_backup_creation(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post(
                "/api/questions",
                json={"question": "同一道题", "type": "0", "options": ["A"], "answer": "正确答案"},
            )
            preview = await client.post(
                "/api/import-json/preview",
                files={
                    "file": (
                        "conflict.json",
                        '[{"question":" 同一道题 ","type":"0","options":["A"],"answer":"另一个答案"}]',
                        "application/json",
                    )
                },
            )
            run_id = preview.json()["data"]["run_id"]
            commit = await client.post("/api/import-json/commit", json={"run_id": run_id})
            backups = await client.get("/api/import-backups")

    assert preview.status_code == 200
    assert preview.json()["data"]["can_commit"] is False
    assert preview.json()["data"]["conflicts"][0]["code"] == "existing_answer_conflict"
    assert commit.status_code == 409
    assert backups.json()["data"] == []


@pytest.mark.anyio
async def test_import_commit_rejects_a_preview_when_matching_question_changes(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            preview = await client.post(
                "/api/import-json/preview",
                files={
                    "file": (
                        "stale.json",
                        '[{"question":"稍后被新增的题目","type":"0","options":[],"answer":"答案"}]',
                        "application/json",
                    )
                },
            )
            await client.post(
                "/api/questions",
                json={"question": "稍后被新增的题目", "type": "0", "options": [], "answer": "答案"},
            )
            commit = await client.post(
                "/api/import-json/commit",
                json={"run_id": preview.json()["data"]["run_id"]},
            )
            questions = await client.get("/api/questions")
            backups = await client.get("/api/import-backups")

    assert commit.status_code == 409
    assert questions.json()["total"] == 1
    assert backups.json()["data"] == []


@pytest.mark.anyio
async def test_import_updates_an_unambiguous_existing_record(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            created = await client.post(
                "/api/questions",
                json={"question": "原始题干", "type": "0", "options": ["A"], "answer": "答案"},
            )
            preview = await client.post(
                "/api/import-json/preview",
                files={
                    "file": (
                        "update.json",
                        '[{"question":" 原始题干 ","type":"0","options":["A "],"answer":"答案"}]',
                        "application/json",
                    )
                },
            )
            commit = await client.post(
                "/api/import-json/commit",
                json={"run_id": preview.json()["data"]["run_id"]},
            )
            questions = await client.get("/api/questions")

    assert created.status_code == 200
    assert preview.json()["data"]["updated"] == 1
    assert preview.json()["data"]["can_commit"] is True
    assert commit.status_code == 200
    assert commit.json()["data"]["updated"] == 1
    assert questions.json()["data"][0]["options"] == ["A "]


@pytest.mark.anyio
async def test_pending_pagination_has_stable_contract_and_duplicate_hints(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/search", json={"question": "  重复   题 ", "type": "0"})
            await client.post("/api/search", json={"question": "重复 题", "type": "0"})
            response = await client.get("/api/pending", params={"page": 1, "page_size": 1})
            second_page = await client.get("/api/pending", params={"page": 2, "page_size": 1})

    body = response.json()
    assert response.status_code == 200
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 2
    assert body["items"] == body["data"]
    assert body["items"][0]["duplicate"] is True
    assert body["items"][0]["duplicate_ids"]
    assert second_page.json()["items"][0]["id"] != body["items"][0]["id"]


@pytest.mark.anyio
async def test_pending_batch_delete_requires_confirmation_and_records_repeatable_batch(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/search", json={"question": "待删除题", "type": "0"})
            pending = await client.get("/api/pending")
            pending_id = pending.json()["items"][0]["id"]
            missing_id = pending_id + 999
            rejected = await client.post(
                "/api/pending/batch/delete",
                json={"ids": [pending_id], "confirm": False},
            )
            result = await client.post(
                "/api/pending/batch/delete",
                json={"ids": [pending_id, missing_id], "confirm": True},
            )
            repeated = await client.post(
                "/api/pending/batch/delete",
                json={"ids": [pending_id, missing_id], "confirm": True},
            )
            history = await client.get("/api/pending/history")

    assert rejected.status_code == 400
    assert result.status_code == 200
    assert result.json()["data"]["success"] == 1
    assert result.json()["data"]["skipped"] == 1
    assert repeated.json()["data"]["success"] == 0
    assert repeated.json()["data"]["skipped"] == 2
    assert history.json()["data"]["total"] == 2
    assert history.json()["items"][0]["actor"] == "local"
    assert history.json()["items"][0]["operation"] == "delete"


@pytest.mark.anyio
async def test_pending_batch_promote_returns_partial_results_and_history(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/search", json={"question": "待转正题", "type": "0"})
            pending = await client.get("/api/pending")
            pending_id = pending.json()["items"][0]["id"]
            result = await client.post(
                "/api/pending/batch/promote",
                json={
                    "items": [
                        {
                            "id": pending_id,
                            "question": "待转正题",
                            "type": "0",
                            "options": [],
                            "answer": "答案",
                        },
                        {
                            "id": pending_id + 999,
                            "question": "已不存在题",
                            "type": "0",
                            "options": [],
                            "answer": "答案",
                        },
                    ]
                },
            )
            questions = await client.get("/api/questions")
            history = await client.get("/api/pending/history", params={"operation": "promote"})

    assert result.status_code == 200
    assert result.json()["data"]["success"] == 1
    assert result.json()["data"]["skipped"] == 1
    assert questions.json()["total"] == 1
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["details"][1]["reason"] == "not_found"


@pytest.mark.anyio
async def test_pending_history_cleanup_keeps_recent_records(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        db = app.state.db
        conn = await db._get_connection()
        try:
            await conn.execute(
                "INSERT INTO pending_operation_history "
                "(batch_id, operation, actor, result, created_at) "
                "VALUES (?, ?, ?, ?, datetime('now', '-91 days'))",
                ("old-batch", "delete", "local", "success"),
            )
            await conn.commit()
        finally:
            await db._release_connection(conn)
        removed = await db.cleanup_pending_operation_history()
        history = await db.get_pending_operation_history()

    assert removed == 1
    assert history["total"] == 0


@pytest.mark.anyio
async def test_search_keeps_legacy_response_and_records_only_a_redacted_audit(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post(
                "/api/questions",
                json={"question": "可审计题目", "type": "0", "options": [], "answer": "答案"},
            )
            response = await client.post(
                "/api/search",
                json={"question": "可审计题目", "type": "0"},
            )
            audits = await client.get("/api/decisions/audit")

    assert response.status_code == 200
    assert response.json()["data"]["answer"] == "答案"
    assert response.json()["data"]["source"] == "local"
    assert audits.status_code == 200
    assert len(audits.json()["data"]) == 1
    audit = audits.json()["data"][0]
    assert audit["answer_digest"]
    assert "答案" not in str(audit)
    assert "可审计题目" not in str(audit)


@pytest.mark.anyio
async def test_search_audit_does_not_change_pending_result(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/search",
                json={"question": "没有答案的题目", "type": "0"},
            )
            pending = await client.get("/api/pending")
            audits = await client.get("/api/decisions/audit")

    assert response.json()["code"] == 0
    assert response.json()["data"]["status"] == "pending"
    assert pending.json()["total"] == 1
    assert audits.json()["data"][0]["status"] == "pending"


@pytest.mark.anyio
async def test_match_quality_is_paginated_redacted_and_expires_after_seven_days(isolated_app):
    app = isolated_app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post(
                "/api/questions",
                json={"question": "质量题目", "type": "0", "options": ["A"], "answer": "正确答案"},
            )
            answered = await client.post(
                "/api/search",
                json={"question": "质量题目", "type": "0", "options": ["A"]},
            )
            pending = await client.post(
                "/api/search",
                json={"question": "质量未命中", "type": "0", "options": ["B"]},
            )
            quality = await client.get(
                "/api/decisions/match-quality", params={"page_size": 1, "found": "true"}
            )
            miss_quality = await client.get(
                "/api/decisions/match-quality", params={"found": "false"}
            )
            conn = await app.state.db._get_connection()
            try:
                await conn.execute(
                    "UPDATE decision_audits SET expires_at = datetime('now', '-1 day')"
                )
                await conn.commit()
            finally:
                await app.state.db._release_connection(conn)
            removed = await app.state.decision_service.cleanup_expired_audits()
            expired = await client.get("/api/decisions/match-quality")

    assert answered.json()["data"]["answer"] == "正确答案"
    assert pending.json()["data"]["status"] == "pending"
    assert quality.status_code == 200
    assert quality.json()["data"]["total"] == 1
    assert len(quality.json()["data"]["items"]) == 1
    item = quality.json()["data"]["items"][0]
    assert item["match_stage"] == "exact_typed"
    assert item["normalized_question_preview"] == "••••"
    assert item["candidate_summaries"][0]["answer_digest"]
    assert "正确答案" not in str(item)
    assert "质量题目" not in str(item)
    assert miss_quality.json()["data"]["total"] == 1
    assert removed == 2
    assert expired.json()["data"]["total"] == 0

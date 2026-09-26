"""
管理接口 - 导入导出、统计
"""

import os
import json
import tempfile
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse

from ..schemas import ImportCommitRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/stats")
async def get_stats(req: Request):
    db = req.app.state.db
    total, pending = await asyncio.gather(db.get_count(), db.get_pending_count())
    return {"code": 1, "data": {"total": total, "pending": pending}}


@router.get("/api/decisions/audit")
async def list_decision_audits(req: Request, limit: int = 100, request_digest: str | None = None):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit 必须在 1-500 之间")
    audits = await req.app.state.decision_service.list_audits(limit, request_digest)
    return {"code": 1, "data": audits}


@router.get("/api/decisions/match-quality")
async def list_match_quality(
    req: Request,
    page: int = 1,
    page_size: int = 20,
    match_stage: str | None = None,
    status: str | None = None,
    found: bool | None = None,
):
    """匹配质量只读工作台数据，不触发搜索、入队或其他写操作。"""
    if page < 1:
        raise HTTPException(status_code=422, detail="page 必须大于等于 1")
    if not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="page_size 必须在 1-100 之间")
    data = await req.app.state.decision_service.list_match_quality(
        page=page,
        page_size=page_size,
        match_stage=match_stage,
        status=status,
        found=found,
    )
    return {"code": 1, "data": data}


@router.post("/api/import-json/preview")
async def preview_import_json(req: Request, file: UploadFile = File(...)):
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
        report = await req.app.state.import_service.preview(content, file.filename or "题库.json")
        return {"code": 1, "data": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"题库导入预检失败: {e}")
        raise HTTPException(status_code=500, detail="题库导入预检失败") from e


@router.post("/api/import-json")
async def legacy_import_json(req: Request, file: UploadFile = File(None)):
    """兼容旧入口，但只执行预检，不再绕过安全提交流程。"""
    if file is None:
        json_file = req.app.state.json_file
        if not os.path.exists(json_file):
            raise HTTPException(status_code=404, detail="找不到默认 JSON 文件")
        with open(json_file, "rb") as source:
            content = source.read(10 * 1024 * 1024 + 1)
        source_name = os.path.basename(json_file)
    else:
        content = await file.read(10 * 1024 * 1024 + 1)
        source_name = file.filename or "题库.json"
    try:
        report = await req.app.state.import_service.preview(content, source_name)
        return {"code": 1, "msg": "预检完成，请确认后提交", "data": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/import-json/commit")
async def commit_import_json(req: Request, request: ImportCommitRequest):
    try:
        result = await req.app.state.import_service.commit(request.run_id)
        return {"code": 1, "msg": "导入成功", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"题库导入提交失败: {e}")
        raise HTTPException(status_code=500, detail="题库导入提交失败") from e


@router.get("/api/import-backups")
async def list_import_backups(req: Request):
    try:
        backups = await req.app.state.import_service.list_backups()
        return {"code": 1, "data": backups}
    except Exception as e:
        logger.error(f"获取题库备份失败: {e}")
        raise HTTPException(status_code=500, detail="获取题库备份失败") from e


@router.post("/api/import-backups/{backup_id}/restore")
async def restore_import_backup(backup_id: str, req: Request):
    try:
        result = await req.app.state.import_service.restore(backup_id)
        return {"code": 1, "msg": "题库备份已恢复", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"恢复题库备份失败: {e}")
        raise HTTPException(status_code=500, detail="恢复题库备份失败") from e


@router.get("/api/export-json")
async def export_json(req: Request):
    db = req.app.state.db
    try:
        questions = await db.get_all_questions_for_export()
        now = datetime.now()
        filename = now.strftime("%Y%m%d%H%M.json")

        temp_dir = tempfile.gettempdir()
        export_file = os.path.join(temp_dir, f"tiku_export_{os.getpid()}_{now.strftime('%Y%m%d%H%M%S')}.json")

        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        def cleanup_temp_file(path: str):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.error(f"清理临时文件失败: {e}")

        background_tasks = BackgroundTasks()
        background_tasks.add_task(cleanup_temp_file, export_file)

        return FileResponse(
            export_file,
            media_type="application/json",
            filename=filename,
            background=background_tasks
        )
    except Exception as e:
        logger.error(f"导出JSON失败: {e}")
        raise HTTPException(status_code=500, detail="导出失败")

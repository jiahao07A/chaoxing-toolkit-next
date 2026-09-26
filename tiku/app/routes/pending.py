"""
待处理题目接口 - /api/pending
"""

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query

from ..schemas import (
    PendingBatchPromoteRequest,
    PendingIdsRequest,
    QuestionCreate,
)
from ..config import MAX_LIMIT, MAX_OFFSET, MAX_SEARCH_LENGTH

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/pending")
async def get_pending_list(
    req: Request,
    limit: int = Query(100, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0, le=MAX_OFFSET),
    search: str = Query("", max_length=MAX_SEARCH_LENGTH),
    sort: str = Query("count"),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=MAX_LIMIT),
):
    db = req.app.state.db
    if page_size is not None:
        limit = page_size
    if page is not None:
        offset = (page - 1) * limit
    questions, total = await asyncio.gather(
        db.get_pending_questions(limit, offset, search, sort),
        db.get_pending_count(search)
    )
    current_page = offset // limit + 1
    return {
        "code": 1,
        # 保留 data/total 以兼容现有管理台，同时提供稳定分页契约。
        "data": questions,
        "items": questions,
        "page": current_page,
        "page_size": limit,
        "total": total,
    }


@router.get("/api/pending/history")
async def get_pending_history(
    req: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    operation: str = Query("", max_length=20),
):
    try:
        history = await req.app.state.db.get_pending_operation_history(page, page_size, operation)
    except Exception as exc:
        logger.exception("获取待处理操作历史失败")
        raise HTTPException(status_code=503, detail="待处理操作历史暂时不可用") from exc
    return {"code": 1, "data": history, **history}


@router.delete("/api/pending/{pending_id}")
async def delete_pending(pending_id: int, req: Request):
    db = req.app.state.db
    success = await db.delete_pending_question(pending_id)
    if not success:
        raise HTTPException(status_code=404, detail="待处理题目不存在")
    return {"code": 1, "msg": "删除成功"}


@router.post("/api/pending/batch/delete")
@router.post("/api/pending/batch-delete")
async def batch_delete_pending(payload: PendingIdsRequest, req: Request):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="批量删除需要 confirm=true")
    try:
        result = await req.app.state.db.batch_delete_pending_questions(payload.ids, confirm=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 1, "msg": "批量删除完成", "data": result}


@router.post("/api/pending/{pending_id}/to-question")
async def pending_to_question(pending_id: int, question: QuestionCreate, req: Request):
    db = req.app.state.db
    question_id = await db.promote_pending_question(pending_id, question)
    if question_id is None:
        raise HTTPException(status_code=404, detail="待处理题目不存在")
    return {"code": 1, "msg": "已添加到题库", "data": {"id": question_id}}


@router.post("/api/pending/batch/promote")
@router.post("/api/pending/batch-to-question")
async def batch_promote_pending(payload: PendingBatchPromoteRequest, req: Request):
    try:
        result = await req.app.state.db.batch_promote_pending_questions(
            [item.model_dump() for item in payload.items]
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 1, "msg": "批量转正完成", "data": result}

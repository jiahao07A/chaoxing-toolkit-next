"""
搜索接口 - POST /api/search
"""

from fastapi import APIRouter, Request

from ..schemas import SearchRequest, SearchResponse
from ..config import API_KEY
from ..answer_service import AnswerService

router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
async def search_answer(request: SearchRequest, req: Request):
    """题目查询接口"""
    if API_KEY and request.key and request.key != API_KEY:
        return SearchResponse(code=0, msg="密钥无效", data={})

    result = await AnswerService(req.app.state.db).search(
        request.question, request.type, request.options
    )
    if result["found"]:
        return SearchResponse(
            code=-1,
            msg="查询成功",
            data={
                "answer": result["answer"],
                "num": result["num"],
                "usenum": result["usenum"],
                "source": result["source"],
                "status": result["status"],
                "stage": result["stage"],
            },
        )
    return SearchResponse(
        code=0,
        msg="未找到答案",
        data={
            "answer": "",
            "source": result["source"],
            "status": result["status"],
            "stage": result["stage"],
        },
    )

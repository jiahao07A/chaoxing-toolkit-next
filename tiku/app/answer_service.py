"""题目查询决策服务。

路由只负责 HTTP 参数和兼容响应，决策顺序集中在这里，方便后续接入旧题库、AI 和 Jev。
"""

from typing import Any, Dict, Optional


class AnswerService:
    """按本地题库优先的顺序查询答案。"""

    def __init__(self, db):
        self.db = db

    async def search(self, question: str, question_type: str, options=None) -> Dict[str, Any]:
        result: Optional[dict] = await self.db.find_by_question(
            question, question_type, options
        )
        if result:
            count = await self.db.get_count()
            return {
                "found": True,
                "answer": result["answer"],
                "source": "local",
                "status": "answered",
                "stage": "local",
                "num": str(count),
                "usenum": "1",
            }

        await self.db.add_pending_question(question, question_type, options)
        return {
            "found": False,
            "answer": "",
            "source": "local",
            "status": "pending",
            "stage": "local",
            "num": "",
            "usenum": "",
        }

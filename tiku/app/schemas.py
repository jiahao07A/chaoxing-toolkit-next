"""
Pydantic 数据模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from .config import MAX_QUESTION_LENGTH, MAX_OPTIONS_COUNT, MAX_SEARCH_LENGTH


class Question(BaseModel):
    id: Optional[int] = None
    question: str
    type: str
    options: List[str] = []
    answer: str


class QuestionCreate(BaseModel):
    question: str = Field(..., max_length=MAX_QUESTION_LENGTH)
    type: str = Field(..., max_length=50)
    options: List[str] = Field(default=[], max_length=MAX_OPTIONS_COUNT)
    answer: str = Field(..., max_length=1000)

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('题目内容不能为空')
        return v.strip()

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, v):
        if not v or not v.strip():
            raise ValueError('答案不能为空')
        return v.strip()

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if v is None:
            return []
        return [opt[:500] for opt in v]


class QuestionUpdate(BaseModel):
    question: Optional[str] = Field(None, max_length=MAX_QUESTION_LENGTH)
    type: Optional[str] = Field(None, max_length=50)
    options: Optional[List[str]] = Field(None, max_length=MAX_OPTIONS_COUNT)
    answer: Optional[str] = Field(None, max_length=1000)

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('题目内容不能为空')
        return v

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('答案不能为空')
        return v

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if v is not None:
            return [opt[:500] for opt in v]
        return v


class SearchRequest(BaseModel):
    question: str = Field(..., max_length=MAX_SEARCH_LENGTH)
    type: str = Field(..., max_length=50)
    key: Optional[str] = Field(None, max_length=100)
    options: Optional[List[str]] = Field(default=None, max_length=MAX_OPTIONS_COUNT)

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('搜索内容不能为空')
        return v.strip()


class SearchResponse(BaseModel):
    code: int
    msg: Optional[str] = None
    data: Optional[dict] = None
    answer: Optional[str] = None


class DecisionRequest(BaseModel):
    """统一决策请求的脱敏前结构，供决策服务和质量审计复用。"""

    question: str = Field(..., max_length=MAX_SEARCH_LENGTH)
    question_type: str = Field(..., max_length=50)
    options: List[str] = Field(default_factory=list, max_length=MAX_OPTIONS_COUNT)


class DecisionCandidateSummary(BaseModel):
    """候选摘要只包含可用于排查匹配质量的非内容字段。"""

    id: Optional[int] = None
    question_digest: str
    type: str
    rank: int
    text_score: float = Field(ge=0, le=1)
    options_score: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    answer_digest: Optional[str] = None


class DecisionResult(BaseModel):
    """决策服务内部结果；正式搜索接口仍返回兼容的 SearchResponse。"""

    found: bool
    answer: str = ""
    source: str
    status: str
    stage: str
    match_stage: str
    failure_reason: Optional[str] = None
    candidates: List[DecisionCandidateSummary] = Field(default_factory=list)


class ImportCommitRequest(BaseModel):
    run_id: str = Field(..., min_length=36, max_length=36)


class PendingIdsRequest(BaseModel):
    """待处理题目批量删除请求。"""

    ids: List[int] = Field(..., min_length=1, max_length=1000)
    confirm: bool = False

    @field_validator('ids')
    @classmethod
    def validate_ids(cls, values):
        if any(value <= 0 for value in values):
            raise ValueError('题目 ID 必须是正整数')
        if len(set(values)) != len(values):
            raise ValueError('题目 ID 不能重复')
        return values


class PendingPromoteItem(BaseModel):
    """单条待处理题目转正所需的明确 ID 和题库内容。"""

    id: int = Field(..., gt=0)
    question: str = Field(..., max_length=MAX_QUESTION_LENGTH)
    type: str = Field(..., max_length=50)
    options: List[str] = Field(default_factory=list, max_length=MAX_OPTIONS_COUNT)
    answer: str = Field(..., max_length=1000)

    @field_validator('question')
    @classmethod
    def validate_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('题目内容不能为空')
        return value

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('答案不能为空')
        return value

    @field_validator('options')
    @classmethod
    def validate_options(cls, values):
        values = values or []
        if any(len(option) > 500 for option in values):
            raise ValueError('单个选项不能超过 500 个字符')
        return values


class PendingBatchPromoteRequest(BaseModel):
    """待处理题目批量转正请求。每条记录必须携带明确的待处理 ID。"""

    items: List[PendingPromoteItem] = Field(..., min_length=1, max_length=1000)

    @field_validator('items')
    @classmethod
    def validate_items(cls, values):
        ids = [item.id for item in values]
        if len(set(ids)) != len(ids):
            raise ValueError('题目 ID 不能重复')
        return values

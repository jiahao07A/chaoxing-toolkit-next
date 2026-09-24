"""脚本配置 API。"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..config_service import ConfigService

router = APIRouter()


class ConfigUpdate(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)
    version: Optional[int] = None


def _service(req: Request) -> ConfigService:
    return req.app.state.config_service


@router.get("/api/config")
async def get_config(req: Request):
    version, config = await _service(req).get()
    is_userscript = (
        req.headers.get("X-Config-Client") == "chaoxing-userscript"
        and not req.headers.get("Origin")
    )
    visible_config = config if is_userscript else ConfigService.redact(config)
    return {"code": 1, "data": {"version": version, "config": visible_config}}


@router.put("/api/config")
async def update_config(payload: ConfigUpdate, req: Request):
    try:
        version, config = await _service(req).update(payload.config, payload.version)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=409 if "版本" in str(exc) else 422, detail=str(exc)) from exc
    return {"code": 1, "msg": "配置已保存", "data": {"version": version, "config": ConfigService.redact(config)}}

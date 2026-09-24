"""本地配置的读取、合并、校验和脱敏。"""

import asyncio
import json
import os
import tempfile
from copy import deepcopy
from typing import Any, Dict, Optional, Tuple


CONFIG_VERSION = 1
SECRET_MARKER = "***"
SECRET_KEY_PARTS = ("key", "token", "password", "secret")

DEFAULT_CONFIG: Dict[str, Any] = {
    "debugger": False,
    "thtoken": "",
    "yztoken": "",
    "gptKey": "",
    "gptModel": "gpt-3.5-turbo",
    "gpt": False,
    "gptType": ["0", "1", "2", "3", "4", "5", "6", "7"],
    "customApiEnabled": True,
    "customApiUrl": "http://localhost:8002/api/search",
    "customApiKey": "",
    "questionBankEnabled": True,
    "tikuHaiEnabled": True,
    "yiZhiEnabled": True,
    "yanXiEnabled": True,
    "mukeEnabled": True,
    "aiEnabled": True,
    "aiApiUrl": "",
    "aiModel": "",
    "aiApiKey": "",
    "aiRetryCount": 3,
    "aiRetryDelay": 1000,
    "jevEnabled": True,
    "jevApiUrl": "",
    "jevModel": "jev-latest",
    "jevApiKey": "",
    "jevMinConfidence": 0.7,
    "interval": 3,
    "answerIntervalMin": 8,
    "answerIntervalMax": 30,
    "submitDelayMin": 20,
    "submitDelayMax": 40,
    "autoAnswer": True,
    "autoVideo": True,
    "autoJump": True,
    "autoSubmit": True,
    "autoExam": True,
    "hideExam": False,
    "notice": "本脚本仅供学习交流使用，严禁用于商业用途，否则后果自负！",
    "deepseekKey": "",
    "deepseekEnabled": False,
    "deepseekModel": "deepseek-reasoner",
    "minAccuracy": 0.8,
    "logEnabled": True,
    "logLevel": "info",
    "logShowQuestion": True,
    "logShowAnswer": True,
    "logShowRequests": True,
    "logShowConfig": True,
    "logShowAi": True,
    "logShowJev": True,
    "logShowLegacy": True,
    "logShowTiming": True,
    "logShowWarnings": True,
    "logShowErrors": True,
    "logQuestionPreviewLength": 50,
    "logAnswerPreviewLength": 120,
}


def _is_secret(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SECRET_KEY_PARTS)


def _validate(config: Dict[str, Any]) -> Dict[str, Any]:
    validated = deepcopy(config)
    for key in ("aiRetryCount",):
        if key in validated:
            value = int(validated[key])
            if not 0 <= value <= 10:
                raise ValueError(f"{key} 必须在 0-10 之间")
            validated[key] = value
    for key in ("aiRetryDelay", "interval", "answerIntervalMin", "answerIntervalMax", "submitDelayMin", "submitDelayMax"):
        if key in validated:
            value = int(validated[key])
            if value < 0 or value > 86400000:
                raise ValueError(f"{key} 超出允许范围")
            validated[key] = value
    if "jevMinConfidence" in validated:
        value = float(validated["jevMinConfidence"])
        if not 0 <= value <= 1:
            raise ValueError("jevMinConfidence 必须在 0-1 之间")
        validated["jevMinConfidence"] = value
    if "minAccuracy" in validated:
        value = float(validated["minAccuracy"])
        if not 0 <= value <= 1:
            raise ValueError("minAccuracy 必须在 0-1 之间")
        validated["minAccuracy"] = value
    if "logLevel" in validated:
        value = str(validated["logLevel"]).lower()
        if value not in {"error", "warn", "info", "debug"}:
            raise ValueError("logLevel 必须是 error、warn、info 或 debug")
        validated["logLevel"] = value
    for key in ("logQuestionPreviewLength", "logAnswerPreviewLength"):
        if key in validated:
            value = int(validated[key])
            if value < 0 or value > 2000:
                raise ValueError(f"{key} 必须在 0-2000 之间")
            validated[key] = value
    for key, value in validated.items():
        if key.endswith("Url") and value and not isinstance(value, str):
            raise ValueError(f"{key} 必须是字符串")
    return validated


class ConfigService:
    def __init__(self, path: str):
        self.path = path
        self._lock = asyncio.Lock()

    def _read(self) -> Tuple[int, Dict[str, Any]]:
        if not os.path.exists(self.path):
            return CONFIG_VERSION, deepcopy(DEFAULT_CONFIG)
        with open(self.path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        version = int(payload.get("version", CONFIG_VERSION))
        stored = payload.get("config", {})
        if not isinstance(stored, dict):
            raise ValueError("配置文件格式错误")
        merged = deepcopy(DEFAULT_CONFIG)
        merged.update(stored)
        return version, merged

    def _write(self, version: int, config: Dict[str, Any]) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="config-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": version, "config": config}, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    async def get(self) -> Tuple[int, Dict[str, Any]]:
        async with self._lock:
            return self._read()

    async def update(self, incoming: Dict[str, Any], expected_version: Optional[int] = None) -> Tuple[int, Dict[str, Any]]:
        async with self._lock:
            version, current = self._read()
            if expected_version is not None and expected_version != version:
                raise ValueError("配置版本已变化，请刷新后重试")
            merged = deepcopy(current)
            for key, value in incoming.items():
                if _is_secret(key) and value == SECRET_MARKER:
                    continue
                merged[key] = value
            merged = _validate(merged)
            version += 1
            self._write(version, merged)
            return version, merged

    @staticmethod
    def redact(config: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(config)
        for key, value in result.items():
            if _is_secret(key) and value:
                result[key] = SECRET_MARKER
        return result

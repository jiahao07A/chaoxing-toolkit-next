"""
Chaoxing Toolkit Next 本地题库服务 - FastAPI 应用工厂
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import (
    DATABASE_FILE, JSON_FILE, CONFIG_FILE, IMPORT_BACKUP_DIR, DEFAULT_PORT, SERVICE_DIR,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW,
    REQUEST_TIMEOUT, MAX_CONCURRENT_REQUESTS, get_cors_origins
)
from .database import AsyncDatabase
from .import_service import ImportService
from .decision_service import DecisionService
from .middleware import RateLimitMiddleware, rate_limiter, concurrency_counter
from .routes import search_router, questions_router, pending_router, admin_router, config_router
from .config_service import ConfigService

logger = logging.getLogger(__name__)

# 全局数据库实例
db: AsyncDatabase = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db
    database_file = getattr(app.state, "database_file", DATABASE_FILE)
    json_file = getattr(app.state, "json_file", JSON_FILE)
    config_file = getattr(app.state, "config_file", CONFIG_FILE)

    db = AsyncDatabase(database_file)
    await db.init_db()

    count = await db.get_count()
    if count == 0:
        await db.import_from_json(json_file)

    # 将 db 注入到 app.state 以便路由访问
    app.state.db = db
    app.state.config_service = ConfigService(config_file)
    app.state.import_service = ImportService(db, app.state.backup_dir)
    app.state.decision_service = DecisionService(db)
    await app.state.decision_service.ensure_audit_table()

    print(f"题库服务器已启动，共 {count} 道题目")
    print(f"并发限制: {MAX_CONCURRENT_REQUESTS}")
    print(f"限流配置: {RATE_LIMIT_REQUESTS} 请求/{RATE_LIMIT_WINDOW}秒")
    print(f"请求超时: {REQUEST_TIMEOUT}秒")

    yield

    print("正在关闭服务器...")
    try:
        if db:
            async with db._pool_lock:
                for conn in db._connection_pool:
                    try:
                        await conn.close()
                    except Exception as e:
                        logger.error(f"关闭数据库连接失败: {e}")
                db._connection_pool.clear()
        print("资源清理完成")
    except Exception as e:
        logger.error(f"资源清理失败: {e}")
    print("题库服务器已关闭")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    logger.warning(f"请求验证错误: {exc}")
    return JSONResponse(
        status_code=422,
        content={"code": 0, "msg": "请求参数错误", "detail": str(exc)}
    )


async def global_exception_handler(request: Request, exc: Exception):
    """处理全局未捕获异常"""
    logger.error(f"未捕获的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 0, "msg": "服务器内部错误"}
    )


def create_app(
    *,
    database_file: Optional[str] = None,
    json_file: Optional[str] = None,
    config_file: Optional[str] = None,
    backup_dir: Optional[str] = None,
) -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="Chaoxing Toolkit Next — 本地题库服务",
        description="个人本机题库管理、答案查询与脚本配置同步；管理接口无身份认证，仅供本机使用",
        version="2.2.0",
        lifespan=lifespan
    )

    # 测试或嵌入式调用可以注入隔离的运行时文件，生产调用继续使用默认配置。
    app.state.database_file = database_file or DATABASE_FILE
    app.state.json_file = json_file or JSON_FILE
    app.state.config_file = config_file or CONFIG_FILE
    app.state.backup_dir = backup_dir or str(IMPORT_BACKUP_DIR)

    @app.get("/api/health")
    async def health_check(req: Request):
        """报告本机服务、数据库和配置文件的可用状态。"""
        database_ok = False
        config_ok = False
        database_detail = {"status": "unavailable"}
        config_detail = {"status": "unavailable"}
        db_instance = getattr(req.app.state, "db", None)
        if db_instance is not None:
            try:
                conn = await db_instance._get_connection()
                try:
                    await conn.execute("SELECT 1")
                    database_ok = True
                    database_detail = {"status": "ok", "questions": await db_instance.get_count()}
                finally:
                    await db_instance._release_connection(conn)
            except Exception:
                database_ok = False
                database_detail = {"status": "error"}
        try:
            await req.app.state.config_service.get()
            config_ok = True
            config_detail = {"status": "ok"}
        except Exception:
            config_ok = False
            config_detail = {"status": "error"}
        status = "ok" if database_ok and config_ok else "degraded"
        return {
            "code": 1 if status == "ok" else 0,
            "status": status,
            "service": {"name": "tiku", "status": status},
            "database": database_ok,
            "database_detail": database_detail,
            "config": config_ok,
            "config_detail": config_detail,
        }

    # 注册异常处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 限流中间件
    app.add_middleware(RateLimitMiddleware)

    # 静态文件
    static_dir = SERVICE_DIR / "static"
    assets_dir = static_dir / "assets"
    os.makedirs(assets_dir, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # 注册 API 路由
    app.include_router(search_router)
    app.include_router(questions_router)
    app.include_router(pending_router)
    app.include_router(admin_router)
    app.include_router(config_router)

    # SPA fallback - 所有非 API、非 assets 的 GET 请求返回 index.html
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa_fallback(full_path: str):
        # 检查是否是静态文件
        static_file = os.path.join(static_dir, full_path)
        if os.path.isfile(static_file):
            from fastapi.responses import FileResponse
            return FileResponse(static_file)
        # 返回 SPA index.html
        index_path = static_dir / "index.html"
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>请先构建前端: cd tiku/frontend && npm run build</h1>")

    return app

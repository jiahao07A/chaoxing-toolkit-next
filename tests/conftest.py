import pytest

from tiku.app import create_app


@pytest.fixture
def anyio_backend():
    """只使用 asyncio，避免测试夹具依赖未安装的 Trio。"""
    return "asyncio"


@pytest.fixture
def isolated_app(tmp_path):
    """为每个测试提供独立的 SQLite、种子和配置文件路径。"""
    json_file = tmp_path / "empty.json"
    json_file.write_text("[]", encoding="utf-8")
    return create_app(
        database_file=str(tmp_path / "questions.db"),
        json_file=str(json_file),
        config_file=str(tmp_path / "config.json"),
        backup_dir=str(tmp_path / "import_backups"),
    )

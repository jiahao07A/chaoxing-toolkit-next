# 题库服务

## 目录边界

- `app/`：FastAPI 应用、路由、匹配和数据库服务。
- `frontend/`：Vue 3 管理界面源码。
- `data/tiku.json`：可提交的题库种子数据。
- `static/`：前端构建产物，已加入忽略规则。
- `legacy/`：旧版模板，仅作历史参考。
- `venv/`、数据库和本机配置：本地运行时文件，不提交。

## 启动

从仓库根目录运行 `scripts/launcher/start-simple.bat`，或进入本目录执行：

```powershell
python main.py
```

默认服务地址为 `http://localhost:8002`。
服务仅绑定本机地址；健康检查为 `http://localhost:8002/api/health`。管理台不使用伪登录，打开后即可使用。

## 运行后端测试

测试使用临时目录中的 SQLite 文件，不会连接或修改本机运行数据库：

```powershell
tiku\venv\Scripts\python.exe -m pip install -r tiku\requirements-dev.txt
tiku\venv\Scripts\python.exe -m pytest -q
```

## 配置契约

修改 `config/settings.schema.json` 后，在仓库根目录运行：

```powershell
python scripts/generate_config_contract.py
```

生成器会同步更新后端、管理台和用户脚本中的配置契约，并写入同一份 schema 哈希。

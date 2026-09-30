# Chaoxing Toolkit Next 题库服务

本地 FastAPI + SQLite 服务，提供题目管理、答案查询、导入预检、备份恢复与用户脚本配置同步。面向可信的单机环境，默认只绑定 `127.0.0.1`，管理台无需登录，也没有身份认证与多用户隔离。

## 首次安装与启动

完整步骤见 [安装、启动与排障](../docs/guides/quick-start.md)。首次使用需创建 `tiku/venv/`、安装 `requirements.txt`，并在 `frontend/` 执行 `npm ci` 与 `npm run build`。仅运行 Python 不会自动构建管理页面。

安装完成后，从仓库根目录启动：

```powershell
.\tiku\venv\Scripts\python.exe .\tiku\main.py
```

macOS/Linux 使用 `tiku/venv/bin/python tiku/main.py`。

- 管理界面：`http://localhost:8002/`
- 健康检查：`http://localhost:8002/api/health`
- API 文档：`http://localhost:8002/docs`
- 题目查询：`POST http://localhost:8002/api/search`，请求字段以 API 文档为准。

`API_KEY` 是查询接口的兼容参数，不是完整认证机制。请保持本机使用，详细边界见 [安全说明](../SECURITY.md)。

## 目录与数据

- `app/`：应用、路由、匹配、配置、导入和数据库服务。
- `frontend/`：Vue 3 管理界面源码。
- `data/tiku.json`：历史题库种子数据，正确性与再分发授权待核验。
- `data/`：默认运行数据库、配置与导入备份目录；个人运行数据不提交。
- `static/`：前端构建产物，已加入忽略规则。
- `legacy/`：旧版模板，仅作历史参考。
- `venv/`：本机 Python 虚拟环境，不提交。

数据路径覆盖和旧版兼容逻辑见 [数据目录说明](data/README.md)。种子 JSON 不是当前数据库备份，升级前应停止服务并备份实际运行数据。

## 开发与测试

后端测试使用临时目录中的数据库和配置，完整命令见 [贡献指南](../CONTRIBUTING.md)。前端开发代理默认指向本机 `8002`，后端须另行启动。

修改 `config/settings.schema.json` 后，在仓库根目录运行：

```powershell
python scripts/generate_config_contract.py
```

生成器会同步后端、管理台和用户脚本中的配置约束及其哈希，再按贡献指南执行回归验证。

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

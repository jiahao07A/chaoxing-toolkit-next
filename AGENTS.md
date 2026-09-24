# AGENTS.md

本项目面向非工程背景的产品协作，优先使用简体中文说明变更、验证结果和待确认事项。

## Agent skills

### Issue tracker

GitHub Issues，默认不把 PR 作为 triage 请求入口。See `docs/agents/issue-tracker.md`.

### Domain docs

单体仓库使用根目录 `CONTEXT.md` 和 `docs/adr/`。See `docs/agents/domain.md`.

## 工作约定

- 修改前检查工作区，保留用户已有改动和未跟踪数据。
- 运行时配置、数据库、缓存和密钥文件不得提交。
- 完成功能后先报告验证结果，用户确认无误后再提交或发布。
- 使用 `pwsh.exe` 执行 Windows 命令，Git 操作用选择性暂存。
- 项目入口见 `README.md`；启动与排障说明统一放在 `docs/guides/`。
- 用户脚本的正式来源是 `scripts/userscript/学习通脚本.js`；修改后同步说明文档中的路径。
- 后端以 `tiku/` 为服务边界，运行数据放在 `tiku/data/`，不得把本机数据库或配置加入 Git。

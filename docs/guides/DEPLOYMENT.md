# 本地部署说明

当前可维护的部署方式是个人本机运行，完整步骤统一见 [安装、启动与排障](quick-start.md)。

首次使用需要创建 Python 虚拟环境、安装后端依赖，并通过 `npm ci` 和 `npm run build` 构建管理界面。前端输出目录为 `tiku/static/`，不使用旧版 `frontend/dist/` 复制步骤。

本项目不提供公共在线服务，不保证固定题库数量或并发性能。管理台没有认证授权；默认仅监听 `127.0.0.1`，不能凭设置 `API_KEY` 就安全暴露到公网。具体边界见 [安全说明](../../SECURITY.md)。

常用入口：

- 管理界面：`http://localhost:8002/`
- 健康检查：`http://localhost:8002/api/health`
- API 文档：`http://localhost:8002/docs`
- 数据与备份：[运行数据目录](../../tiku/data/README.md)
- 开发测试：[贡献指南](../../CONTRIBUTING.md)

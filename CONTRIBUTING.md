# 贡献与问题反馈

当前项目入口是 [jiahao07A/chaoxing-toolkit-next](https://github.com/jiahao07A/chaoxing-toolkit-next)，使用简体中文协作。请先阅读 [README](README.md)、[来源与授权状态](NOTICE.md) 和 [安全说明](SECURITY.md)。

## 提交问题

使用 [GitHub Issues](https://github.com/jiahao07A/chaoxing-toolkit-next/issues) 报告一般故障、提出功能建议或讨论设计。建议包含：

1. 你希望完成的操作、预期结果与实际结果。
2. 可复现步骤，及涉及的是用户脚本、后端还是管理界面。
3. 脚本版本或 Git 提交编号，以及浏览器、Tampermonkey、Python/Node.js 的相关版本。
4. 已尝试的排查方法和经过脱敏的错误日志或截图。

页面地址只提供必要域名和页面类型，不要上传完整的带账号、课程及访问参数的 URL。避免提交个人题库、密钥、Cookies 和真实账号。安全问题按 [SECURITY.md](SECURITY.md) 处理。

## 开发环境

先按 [快速开始](docs/guides/quick-start.md) 安装依赖并完成前端构建。管理界面开发服务器可从根目录启动：

```powershell
npm --prefix tiku/frontend run dev
```

Vite 通常使用 `http://localhost:5173`，其中 `/api` 通过开发代理转发到本机 `8002` 后端；仍需单独启动后端。正式静态资源使用 `npm --prefix tiku/frontend run build` 构建，不提交 `tiku/static/` 和 `node_modules/`。

模块边界见 [CONTEXT.md](CONTEXT.md) 和 [架构决策](docs/adr/0001-project-layout.md)。正式用户脚本只有 `scripts/userscript/学习通脚本.js`；历史或参考脚本不是功能修改入口。

## 验证改动

从仓库根目录运行后端测试；它们使用临时数据库和配置，不应连接个人题库：

```powershell
.\tiku\venv\Scripts\python.exe -m pip install -r .\tiku\requirements-dev.txt
.\tiku\venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_userscript_regressions.py -q
```

用户脚本的语法与 Node.js 回归测试：

```powershell
node --check scripts/userscript/学习通脚本.js
node --test scripts/userscript/answer-parser-regression.test.mjs scripts/userscript/automation-regression.test.mjs scripts/userscript/chapter-startup-regression.test.mjs scripts/userscript/settings-dialog-layout.test.mjs scripts/userscript/video-diagnostics-core.test.mjs scripts/userscript/video-playback-regression.test.mjs tests/video_playback.test.cjs
```

前端修改还需运行构建。涉及真实页面行为时，按 [人工测试清单](docs/guides/manual-testing.md) 验证；自动测试通过不意味着所有学习通页面均兼容。请如实列出未验证的系统或场景。

修改 `config/settings.schema.json` 后，从根目录运行 `python scripts/generate_config_contract.py`，同步后端、管理台与用户脚本中的生成内容，再重新测试。

## 提交与评审

- 优先针对一个问题提交小范围变更，并同步相关用户指引。
- 提交前检查 `git diff --check` 和差异内容，使用明确文件路径选择性暂存。
- 不提交运行数据库、密钥、本机配置、缓存、日志、备份、依赖目录和构建产物。
- 大范围改动先在 Issue 中讨论；Pull Request 用于提交和评审实现，不代替问题反馈入口。
- 维护者确认验证结果后再提交或发布，不承诺接受所有建议或固定响应时限。

当前项目未声明统一许可证。提交涉及第三方代码或题目资料的内容时，请说明来源与适用授权；贡献提交本身不会解决原作授权问题。

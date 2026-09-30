# Chaoxing Toolkit Next

学习通学习辅助与本地题库管理工具，由 Tampermonkey 用户脚本和可选的本地题库服务组成，支持题目查询、待处理题目管理、配置同步，以及自行配置的 AI 答案建议。

本仓库由 `jiahao07A` 独立维护，不是超星官方产品，也不代表原项目或原脚本作者。历史来源与授权状态见 [来源说明](NOTICE.md)。

[快速开始](docs/guides/quick-start.md) · [文档导航](docs/README.md) · [反馈问题](https://github.com/jiahao07A/chaoxing-toolkit-next/issues) · [参与贡献](CONTRIBUTING.md) · [安全说明](SECURITY.md)

## 使用前了解

- 本项目面向个人本机学习辅助、题库整理与技术研究。请先确认学校、课程及平台规则允许使用；不得用于代学、考试作弊或绕过平台验证。
- 题库匹配与 AI 建议均可能出错，需要人工核对；不承诺答案正确率、成绩或所有页面的兼容性。
- 本地服务默认仅监听 `127.0.0.1`，管理界面没有登录和权限控制。仓库公开不意味着服务可以安全暴露到公网或作为多人托管服务。
- 第三方题库、AI 服务和脚本依赖可能产生外部请求。题库查询与 AI 请求可能发送题干、选项等内容；启用前请确认数据权限、服务条款和费用。
- 当前仓库尚未提供统一许可证。公开可浏览不等于获得任意复制、再分发或商业使用授权，详情见 [来源与授权状态](NOTICE.md)。
- 当前前端依赖检查存在待处理的安全告警，详情见 [已知依赖告警](SECURITY.md#已知依赖告警)；本次内容整理不代表全面安全审计。

## 可以做什么

| 模块 | 当前功能 | 使用边界 |
| --- | --- | --- |
| 浏览器用户脚本 | 可视化设置、题库查询、答案填入、课程任务与视频播放辅助 | 依赖页面结构和平台规则，平台更新可能影响功能；验证须手动完成 |
| 本地题库服务 | 题目增删改查、待处理题目、导入预检、导出、备份与恢复、匹配质量查看 | 适合单机使用，导入的题目及答案须自行核验 |
| 配置与日志 | 管理台和用户脚本配置同步、日志开关、本地脱敏视频诊断 | 运行配置和诊断数据不是公共题库，不应上传到仓库或 Issues |
| 可选 AI 接口 | 题库未命中时请求兼容接口提供答案建议 | 需自行提供服务地址、模型及密钥，可能产生费用，不包含免费额度 |

用户脚本可以独立安装。只有需要自建题库或服务端配置同步时，才需要运行题库服务；单独使用第三方接口时，无需安装 Python 和 Node.js。

## 快速开始

### 1. 安装用户脚本

1. 在 Chrome、Edge 或 Firefox 中安装 [Tampermonkey](https://www.tampermonkey.net/)。
2. 打开本仓库的正式脚本 [`scripts/userscript/学习通脚本.js`](scripts/userscript/学习通脚本.js)，复制完整内容。
3. 在 Tampermonkey 管理面板选择“添加新脚本”，替换默认内容并保存。
4. 打开允许使用辅助工具的学习通页面，确认脚本已启用，再在页面中的脚本设置入口检查题库、AI 和自动处理开关。

已有旧版脚本时，请先备份原脚本及记录配置，在现有条目中替换内容，避免同时启用多个版本。脚本名称已统一为 `Chaoxing Toolkit Next`；保留原有命名空间，不配置原作者地址自动更新。不同安装方式可能生成新条目，升级后应核对配置。详细步骤见 [用户脚本安装与升级](docs/guides/quick-start.md#用户脚本安装与升级)。

### 2. 可选：启动本地题库服务

准备 **Python 3.11+、Node.js 22.12+（推荐 24 LTS）和 npm**。下面是在 Windows PowerShell 中从全新克隆开始的完整步骤，不需要激活虚拟环境：

```powershell
git clone https://github.com/jiahao07A/chaoxing-toolkit-next.git
Set-Location chaoxing-toolkit-next
python -m venv tiku/venv
.\tiku\venv\Scripts\python.exe -m pip install -r .\tiku\requirements.txt
npm --prefix .\tiku\frontend ci
npm --prefix .\tiku\frontend run build
.\tiku\venv\Scripts\python.exe .\tiku\main.py
```

首次构建前端是必需步骤；构建产物自动写入 `tiku/static/`，无需手动复制。完整的 [Windows、macOS/Linux 安装与排障说明](docs/guides/quick-start.md) 包含健康检查、停止服务和后续启动方法。

启动后打开：

- 管理界面：`http://localhost:8002/`，仅本机使用，无需登录。
- 健康检查：`http://localhost:8002/api/health`，正常时返回 `status: "ok"`。
- API 文档：`http://localhost:8002/docs`。

在用户脚本设置中启用自定义题库，并填写 `http://localhost:8002/api/search`。题库开关和地址是否生效，请结合脚本查询日志核对。停止前台服务可按 `Ctrl+C`。

## 配置与数据

默认端口为 `8002`。在启动后端前设置环境变量，可以调整端口和运行数据目录：

| 环境变量 | 默认值或行为 | 说明 |
| --- | --- | --- |
| `PORT` | `8002` | 修改后须同步调整脚本接口地址与前端开发代理 |
| `WORKERS` | `1` | 后端进程数，单机使用建议保留默认值 |
| `TIKU_DATA_DIR` | `tiku/data/` | 数据库、配置及导入备份的默认存放目录 |
| `DATABASE_FILE` / `JSON_FILE` / `CONFIG_FILE` | 根据数据目录确定 | 单独覆盖数据库、种子数据或配置文件路径 |
| `IMPORT_BACKUP_DIR` | 数据目录下的 `import_backups/` | 导入备份存放位置 |
| `CORS_ORIGINS` | 本机管理界面来源 | 逗号分隔的允许来源；不能替代身份认证 |
| `API_KEY` | `your_api_key` | 查询接口的兼容参数，不是完整的访问控制 |

当前查询接口仅在请求携带非空 `key` 时校验其值；管理接口也没有身份认证。设置 `API_KEY` 不会让服务具备公网部署所需的认证保护。更多边界见 [安全说明](SECURITY.md)。

- `tiku/data/tiku.json` 是随仓库保留的历史种子数据，不保证题目覆盖、答案准确性或再分发授权。仅在本机数据库为空时尝试导入，不会持续覆盖已有题库。
- `questions.db`、`config.json`、导入备份、日志、虚拟环境及构建产物属于本机数据，已列入 Git 忽略规则。
- 服务兼容旧版 `tiku/` 根目录中的数据库和配置；升级前请备份实际使用的文件，详见 [数据目录说明](tiku/data/README.md)。

## 项目结构

```text
scripts/userscript/学习通脚本.js  正式用户脚本
scripts/launcher/              本地启动和停止工具
tiku/app/                      FastAPI 后端及匹配、配置、导入服务
tiku/frontend/                 Vue 3 + Element Plus 管理界面
tiku/data/                     种子数据和本机运行数据
tiku/static/                   本机构建生成的前端页面（不提交）
config/settings.schema.json    前后端与脚本共享的配置约束
tests/                         Python 与部分 Node.js 回归测试
docs/                          使用指南、研究记录、架构与历史说明
```

技术栈：用户脚本使用 Vue、Pinia、Element Plus 和 Tampermonkey API；后端使用 Python、FastAPI、uvicorn、aiosqlite 与 SQLite；管理界面使用 Vue 3、Element Plus 与 Vite。

## 开发与反馈

- 使用问题和功能建议请提交到 [本仓库 Issues](https://github.com/jiahao07A/chaoxing-toolkit-next/issues)，附上复现步骤、版本和脱敏日志。
- 开发环境、回归测试与提交约定见 [贡献指南](CONTRIBUTING.md)。
- 页面功能人工验收见 [测试清单](docs/guides/manual-testing.md)。
- API 密钥、账号、Cookies、个人数据库及安全漏洞细节请勿公开上传；报告方式见 [安全说明](SECURITY.md)。

## 来源与授权

本项目保留了原仓库和原用户脚本的历史来源及作者署名，独立维护不改变这些内容的权利归属。第三方接口和依赖分别遵循其自身条款。详见 [NOTICE.md](NOTICE.md)。

# 安装、启动与排障

本指南适用于 `jiahao07A/chaoxing-toolkit-next` 当前 `main` 分支。所有命令如无特别说明，均从仓库根目录执行。

## 选择使用方式

- 只使用浏览器用户脚本：安装 Tampermonkey 并导入脚本即可，不需要题库服务器。
- 使用自建题库或服务端配置同步：另外安装 Python、Node.js，完成后端依赖安装和管理界面构建。

服务默认仅绑定本机地址，适合单机使用。公开仓库不是在线服务，也不提供公共题库接口或 AI 密钥。使用前请阅读 [项目边界](../../README.md#使用前了解) 与 [安全说明](../../SECURITY.md)。

## 用户脚本安装与升级

1. 从 [Tampermonkey 官网](https://www.tampermonkey.net/) 安装适用于浏览器的扩展；按浏览器和扩展的提示允许用户脚本运行。
2. 打开正式文件 [`scripts/userscript/学习通脚本.js`](../../scripts/userscript/学习通脚本.js)，通过 GitHub 的 Raw 视图或本地文本编辑器复制完整内容。不要复制 README 中的示例，也不要使用参考脚本或历史版本代替正式文件。
3. 在 Tampermonkey 管理面板添加脚本，替换编辑器默认内容并保存。当前脚本名称是 `Chaoxing Toolkit Next｜学习通辅助与本地题库`。
4. 在允许使用辅助工具的学习通页面确认脚本已启用，通过页面中的脚本设置入口检查相关开关。扩展菜单用于管理脚本是否启用，不等于功能配置面板。
5. 新用户先检查自动处理、题库和 AI 设置，确认权限及数据流向后再按需启用。当前实现仍包含部分自动处理默认项，不是只读浏览工具。

已有旧版时：先备份 Tampermonkey 中的脚本并记录个人配置，再在现有条目中替换代码。仓库保留旧命名空间，不设置原脚本的自动更新地址；不同安装方式可能产生新条目或独立存储，更新后须检查配置并停用重复条目。不要通过清空脚本存储排障，这会删除个人设置。

脚本匹配规则包含学习通及部分学校域名，网络连接权限列在文件头部的 `@connect` 中。使用自定义域名的接口时，可能需要追加对应域名并在 Tampermonkey 中批准连接；按需授权，不建议添加 `*`。账号登录、验证码和微信验证须由用户手动完成；验证提示出现后完成验证并刷新页面。

## 本地服务的环境要求

- Python 3.11 或更新版本。
- Node.js 22.12 或更新版本，推荐 Node.js 24 LTS；使用随 Node.js 提供的 npm。
- Git（克隆仓库时需要，也可在 GitHub 下载源码 ZIP）。
- 安装 Python 包和 npm 依赖需要能访问相应包源；用户脚本还需能加载文件头部列出的第三方依赖。

### Windows PowerShell

```powershell
git clone https://github.com/jiahao07A/chaoxing-toolkit-next.git
Set-Location chaoxing-toolkit-next
python -m venv tiku/venv
.\tiku\venv\Scripts\python.exe -m pip install -r .\tiku\requirements.txt
npm --prefix .\tiku\frontend ci
npm --prefix .\tiku\frontend run build
.\tiku\venv\Scripts\python.exe .\tiku\main.py
```

这些命令直接使用虚拟环境中的 Python，不依赖 PowerShell 的激活脚本，也无需调整执行策略。若本机用 `py` 命令管理 Python，可把创建环境的命令改为 `py -3 -m venv tiku/venv`，并确认其选中的 Python 版本满足要求。

### macOS / Linux

```bash
git clone https://github.com/jiahao07A/chaoxing-toolkit-next.git
cd chaoxing-toolkit-next
python3 -m venv tiku/venv
tiku/venv/bin/python -m pip install -r tiku/requirements.txt
npm --prefix tiku/frontend ci
npm --prefix tiku/frontend run build
tiku/venv/bin/python tiku/main.py
```

某些 Linux 发行版需要先通过系统包管理器安装对应版本的 Python `venv` 支持。

### 启动完成的检查

1. 浏览器打开 `http://localhost:8002/`，应显示题库管理界面，而不是旧登录页或“请先构建前端”提示。
2. 打开 `http://localhost:8002/api/health`，正常时 JSON 中 `status` 为 `ok`，`database`、`config` 为 `true`。
3. 在管理界面检查题库数量、待处理题目和配置页；不要以历史文档中的题目数量作为验收标准。
4. 在用户脚本设置中启用题库及自定义题库，填写 `http://localhost:8002/api/search`，再通过日志确认请求确实发往该地址。

健康检查可在另一个 PowerShell 窗口执行：

```powershell
Invoke-RestMethod http://localhost:8002/api/health
```

前端构建直接输出到 `tiku/static/`，无需从 `frontend/dist/` 手动复制。

## 后续启动与停止

完成首次安装后，从仓库根目录再次启动：

```powershell
.\tiku\venv\Scripts\python.exe .\tiku\main.py
```

macOS/Linux 使用 `tiku/venv/bin/python tiku/main.py`。在启动终端按 `Ctrl+C` 停止前台服务。

Windows 可选运行 `scripts/launcher/start-simple.bat`，它要求 `tiku/venv/` 已准备好且前端已构建，并尝试从默认安装路径打开 Chrome 的 `Default` 配置。没有安装 Chrome 或其路径不同时，请使用上面的直接启动方法，手动打开自己的浏览器。

批处理启动器会在独立窗口运行服务，关闭启动器不代表服务已停止。使用 `scripts/launcher/stop.bat` 前先确认其行为：它会强制停止监听所配置端口的进程，不会验证该进程是否属于本项目；推荐优先在服务窗口按 `Ctrl+C`。修改了服务端口时也须同步修改停止脚本的 `TIKU_PORT`。

`start.py` 和 `start-linux.sh` 是可选启动辅助工具，不是首次安装的必要步骤。不同系统上的浏览器自动打开和多进程模式未在本指南中保证可用，遇到问题以直接启动流程为准。

## 端口与数据

PowerShell 中调整端口后启动：

```powershell
$env:PORT = '8003'
.\tiku\venv\Scripts\python.exe .\tiku\main.py
```

修改端口后，将脚本题库地址同步改为 `http://localhost:8003/api/search`；开发模式还需修改 `tiku/frontend/vite.config.js` 的代理目标。

默认运行数据目录为 `tiku/data/`，包括 `questions.db`、`config.json` 和 `import_backups/`。`tiku/data/tiku.json` 是种子数据，不等于当前数据库备份。服务会兼容旧版 `tiku/` 根目录的数据文件；路径覆盖方式见 [数据目录说明](../../tiku/data/README.md)。

升级前先停止服务并备份实际使用的数据库、配置和备份目录。个人数据应保存在 Git 忽略的本机目录中，不要提交密钥、账号或受保护题目。恢复题库前请核对备份内容及恢复范围。

## 常见问题

### 页面提示“请先构建前端”或显示旧登录页

从仓库根目录运行 `npm --prefix tiku/frontend ci` 和 `npm --prefix tiku/frontend run build`，随后重启后端并刷新浏览器。当前管理台没有登录功能；旧截图和历史模板不代表当前界面。

### Node.js 版本报错或构建失败

检查 `node --version` 和 `npm --version`。当前 Vite 依赖需要较新的 Node.js，建议使用 Node.js 24 LTS。保留 `package-lock.json` 并使用 `npm ci`，不要用删除锁文件的方式绕过版本问题。

### Python 缺少模块

使用同一虚拟环境的 Python 安装依赖和启动服务。例如 Windows 中使用 `.\tiku\venv\Scripts\python.exe -m pip install -r .\tiku\requirements.txt`，避免把包安装到系统 Python 后却用另一个解释器运行服务。

### 端口被占用或服务无法访问

查看启动终端的完整错误，先确认是否已有服务占用 `8002`，再停止已确认的进程或调整端口。不要为了访问服务改成 `0.0.0.0`；管理接口没有认证保护。

### 脚本没有界面、依赖报错或题库请求失败

参阅 [用户脚本排障](脚本界面问题排查.md)。先检查脚本是否启用、依赖是否加载、请求权限和接口地址，再排查具体页面；不要同时启用旧版与新版。

### AI 或题库答案不符合预期

确认相关服务、模型、密钥、题库开关和日志。第三方服务可能限流、收费、失效或返回错误答案；需要人工核验，不能以接口请求成功等同于答案正确。

仍无法解决时，请按 [贡献指南](../../CONTRIBUTING.md) 提交脱敏复现信息到 [本仓库 Issues](https://github.com/jiahao07A/chaoxing-toolkit-next/issues)。

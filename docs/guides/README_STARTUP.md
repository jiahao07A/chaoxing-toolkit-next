# 启动器使用说明

启动器是完成首次安装后的可选便利工具，不会代替后端依赖安装和前端构建。请先按 [安装、启动与排障](quick-start.md) 准备环境。

## 推荐的直接启动方式

从仓库根目录执行：

```powershell
.\tiku\venv\Scripts\python.exe .\tiku\main.py
```

macOS/Linux 使用 `tiku/venv/bin/python tiku/main.py`。手动打开 `http://localhost:8002/`，在启动终端按 `Ctrl+C` 停止服务。这种方式不依赖 Chrome 是否安装，也便于查看错误输出。

## 可选工具

| 文件 | 用途与限制 |
| --- | --- |
| `scripts/launcher/start-simple.bat` | Windows 下启动独立服务窗口，尝试从默认安装路径打开 Chrome 和学习通；要求既有虚拟环境和前端构建 |
| `scripts/launcher/start.bat` | Windows 下调用 Python 启动器，浏览器路径与配置仍可能需要调整 |
| `scripts/launcher/start.py` | Python 启动辅助工具，包含不同系统的浏览器检测；未保证每种安装路径均可用 |
| `scripts/launcher/start-linux.sh` | Linux 辅助工具，可安装后端依赖；不会构建前端，多进程模式不作为并发性能承诺 |
| `scripts/launcher/stop.bat` | Windows 下强制停止指定端口的监听进程；不会核验进程是否属于本项目 |

Windows 批处理默认使用 Chrome 的 `Default` 配置目录。它不是邮箱或学习通账号，不会自动替你登录。浏览器配置可通过 `chrome://version/` 查看“个人资料路径”，再按需设置 `CHROME_PROFILE`；服务端口对应 `TIKU_PORT`。

关闭批处理启动器不等于停止独立服务窗口。优先在服务窗口停止；使用 `stop.bat` 前确认端口和进程，避免停止其他程序。修改端口时同步更新脚本接口地址及停止脚本配置。

管理台没有登录认证，仅绑定本机使用。健康检查为 `http://localhost:8002/api/health`。具体错误请使用 [统一排障流程](quick-start.md#常见问题)；反馈前移除账号、邮箱、密钥和课程参数。

# 启动脚本使用说明

## 快速启动

### Windows 用户

双击运行 `scripts/launcher/start.bat` 或在命令行中执行：

```cmd
scripts/launcher/start.bat
```

### 所有平台（推荐）

使用 Python 脚本：

```bash
python scripts/launcher/start.py
```

## 功能说明

启动脚本会自动完成以下操作：

1. ✅ 启动题库服务器（端口 8002）
2. ✅ 打开 Chrome 浏览器（使用配置 `jiahao071016001@gmail.com`）
3. ✅ 自动打开题库管理界面（仅本机访问，无需登录）
4. ✅ 自动打开学习通界面

## 配置说明

### 修改 Chrome 配置文件

编辑 `scripts/launcher/start.py` 或 `scripts/launcher/start.bat`，修改以下变量：

```python
# scripts/launcher/start.py
CHROME_PROFILE = "jiahao071016001@gmail.com"  # 改为你的 Chrome 配置名称
```

```batch
REM scripts/launcher/start.bat
set "CHROME_PROFILE=jiahao071016001@gmail.com"
```

### 修改端口

如果 8002 端口被占用，可以修改：

```python
# scripts/launcher/start.py
TIKU_PORT = 8002  # 改为其他端口，如 8003
```

```batch
REM scripts/launcher/start.bat
set "TIKU_PORT=8002"
```

### 本机访问与健康检查

管理台不再使用伪登录或 URL 凭据。服务默认绑定 `127.0.0.1`，只接受本机访问；启动后可打开 `http://localhost:8002`。

健康检查地址为 `http://localhost:8002/api/health`，会报告服务、SQLite 数据库和本地配置状态。

默认 CORS 只允许本机来源。前端开发服务器如需跨域调试，可在启动后端前设置 `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`；Windows PowerShell 示例：`$env:CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173'; python tiku/main.py`。不要把来源设置为 `*`。

## 使用流程

1. **运行启动脚本**
   ```bash
   python scripts/launcher/start.py
   ```

2. **等待服务器启动**
   - 脚本会自动检测服务器是否就绪
   - 看到 "✓ 题库服务器已启动" 即表示成功

3. **浏览器自动打开**
   - 题库管理界面会直接打开
   - 学习通界面会自动打开

4. **配置用户脚本**
   - 在 Tampermonkey 中打开脚本设置
   - 启用自定义题库
   - 填入题库地址: `http://localhost:8002/api/search`

5. **开始使用**
   - 在学习通页面做题时，脚本会自动调用题库 API
   - 在题库管理界面可以查看、添加、导入题目

## 停止服务

### scripts/launcher/start.py
按 `Ctrl+C` 停止服务器并退出

### scripts/launcher/start.bat
按任意键停止服务器并退出

## 常见问题

### Q: Chrome 无法找到配置文件

**A**: 确保 Chrome 配置文件名称正确。查看方法：
1. 打开 `chrome://version/`
2. 查看 "个人资料路径" 中的 `Profile` 或 `Default` 文件夹名称
3. 将该名称填入脚本的 `CHROME_PROFILE` 变量

### Q: 服务器启动失败

**A**: 检查以下几点：
1. 虚拟环境是否正确安装：`tiku/venv/Scripts/python.exe` 是否存在
2. 依赖是否安装：运行 `pip install -r requirements.txt`
3. 端口是否被占用：尝试修改 `TIKU_PORT` 为其他端口

### Q: 浏览器未自动打开

**A**: 
1. 检查 Chrome 是否已安装
2. Windows: 确认路径 `C:\Program Files\Google\Chrome\Application\chrome.exe`
3. 手动修改脚本中的 `CHROME_PATH` 变量

### Q: 管理台打不开或接口无响应

**A**:
1. 打开 `http://localhost:8002/api/health` 查看服务、数据库和配置状态。
2. 确保端口没有被其他程序占用，并重启服务器。
3. 管理台只绑定本机；远程设备无法访问是预期行为。

## 手动启动（备选方案）

如果自动脚本出现问题，可以手动启动：

```bash
# 1. 启动服务器
cd tiku
./venv/Scripts/python.exe main.py

# 2. 打开浏览器（新终端）
chrome --profile-directory="jiahao071016001@gmail.com" http://localhost:8002
chrome --profile-directory="jiahao071016001@gmail.com" https://i.chaoxing.com/base
```

## 技术细节

### scripts/launcher/start.py 特性

- 自动检测 Chrome 路径（Windows/macOS/Linux）
- 智能等待服务器就绪
- 优雅关闭（Ctrl+C 自动清理）
- 跨平台支持

### scripts/launcher/start.bat 特性

- 纯 Windows 批处理
- 无需额外依赖
- 自动检测服务状态
- 按键退出并清理

## 安全提示

⚠️ **注意**: 当前管理台不提供认证授权，只绑定本机地址并拒绝默认跨域来源。若要暴露到其他设备，必须先补充正式认证和网络隔离方案。

## 更新日志

- **2026-09-26**: 收紧本机安全边界
  - 移除伪登录、sessionStorage 登录标记和 URL 明文凭据
  - 默认绑定 localhost，增加 `/api/health` 健康检查
- **2026-09-23**: 创建启动脚本
  - 支持自动启动服务器
  - 支持自动打开浏览器
  - 支持跨平台（Windows/macOS/Linux）

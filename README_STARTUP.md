# 启动脚本使用说明

## 快速启动

### Windows 用户

双击运行 `start.bat` 或在命令行中执行：

```cmd
start.bat
```

### 所有平台（推荐）

使用 Python 脚本：

```bash
python start.py
```

## 功能说明

启动脚本会自动完成以下操作：

1. ✅ 启动题库服务器（端口 8002）
2. ✅ 打开 Chrome 浏览器（使用配置 `jiahao071016001@gmail.com`）
3. ✅ 自动打开并登录题库管理界面
4. ✅ 自动打开学习通界面

## 配置说明

### 修改 Chrome 配置文件

编辑 `start.py` 或 `start.bat`，修改以下变量：

```python
# start.py
CHROME_PROFILE = "jiahao071016001@gmail.com"  # 改为你的 Chrome 配置名称
```

```batch
REM start.bat
set "CHROME_PROFILE=jiahao071016001@gmail.com"
```

### 修改端口

如果 8002 端口被占用，可以修改：

```python
# start.py
TIKU_PORT = 8002  # 改为其他端口，如 8003
```

```batch
REM start.bat
set "TIKU_PORT=8002"
```

### 修改登录账号

默认账号为 `admin/admin`，如需修改：

```python
# start.py
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
```

然后修改前端 `tiku/frontend/src/views/Login.vue` 中的验证逻辑。

## 自动登录功能

前端已支持 URL 参数自动登录：

```
http://localhost:8002/#/login?auto=1&user=admin&pass=admin
```

参数说明：
- `auto=1`: 启用自动登录
- `user`: 用户名
- `pass`: 密码

## 使用流程

1. **运行启动脚本**
   ```bash
   python start.py
   ```

2. **等待服务器启动**
   - 脚本会自动检测服务器是否就绪
   - 看到 "✓ 题库服务器已启动" 即表示成功

3. **浏览器自动打开**
   - 题库管理界面会自动登录
   - 学习通界面会自动打开

4. **配置用户脚本**
   - 在 Tampermonkey 中打开脚本设置
   - 启用自定义题库
   - 填入题库地址: `http://localhost:8002/api/search`

5. **开始使用**
   - 在学习通页面做题时，脚本会自动调用题库 API
   - 在题库管理界面可以查看、添加、导入题目

## 停止服务

### start.py
按 `Ctrl+C` 停止服务器并退出

### start.bat
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

### Q: 自动登录不工作

**A**: 
1. 确保前端已重新构建：`cd tiku/frontend && npm run build`
2. 确保静态文件已更新：`cp -r frontend/dist/* static/`
3. 重启服务器

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

### start.py 特性

- 自动检测 Chrome 路径（Windows/macOS/Linux）
- 智能等待服务器就绪
- 优雅关闭（Ctrl+C 自动清理）
- 跨平台支持

### start.bat 特性

- 纯 Windows 批处理
- 无需额外依赖
- 自动检测服务状态
- 按键退出并清理

### 自动登录实现

前端 `Login.vue` 监听 URL 参数：
```javascript
onMounted(() => {
  if (route.query.auto === '1') {
    username.value = route.query.user
    password.value = route.query.pass
    setTimeout(handleLogin, 500)
  }
})
```

## 安全提示

⚠️ **注意**: URL 参数中包含明文密码，仅适用于本地开发环境。生产环境请使用更安全的认证方式（如 Token、Cookie 等）。

## 更新日志

- **2026-09-23**: 创建启动脚本
  - 支持自动启动服务器
  - 支持自动打开浏览器
  - 支持自动登录管理界面
  - 支持跨平台（Windows/macOS/Linux）

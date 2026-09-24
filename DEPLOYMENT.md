# 超星学习通题库系统 - 部署说明

## 部署完成状态

✅ **服务器已成功部署并运行**

- **服务地址**: http://localhost:8002
- **API 接口**: http://localhost:8002/api/search
- **管理界面**: http://localhost:8002/
- **API 文档**: http://localhost:8002/docs
- **题库数量**: 1036 道题目

## 部署步骤记录

### 1. 后端部署

```bash
cd chaoxing-toolkit/tiku

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
./venv/Scripts/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 前端构建

```bash
cd frontend

# 安装依赖
npm install

# 构建前端资源
npm run build

# 复制构建文件到 static 目录
cd ..
cp -r frontend/dist/* static/
```

### 3. 启动服务器

```bash
# 使用环境变量指定端口（默认 8001，如有冲突可更改）
PORT=8002 ./venv/Scripts/python.exe main.py
```

## API 测试

### 查询答案示例

```bash
curl -X POST http://localhost:8002/api/search \
  -H "Content-Type: application/json" \
  -d '{"question":"支撑搭设流程正确的方法是什么？","type":"0"}'
```

**响应示例**:
```json
{
  "code": -1,
  "msg": "查询成功",
  "data": {
    "answer": "A",
    "num": "1036",
    "usenum": "1"
  }
}
```

### 查询题目列表

```bash
curl -s "http://localhost:8002/api/questions?page=1&page_size=10"
```

## 使用说明

### 用户脚本安装

1. 安装 [Tampermonkey 浏览器扩展](https://www.tampermonkey.net/)
2. 打开 `学习通脚本.js` 文件
3. 在 Tampermonkey 中创建新脚本，粘贴内容并保存
4. 在脚本设置中配置题库服务器地址: `http://localhost:8002/api/search`

### 管理界面功能

访问 http://localhost:8002/ 可以：
- 查看所有题目
- 搜索题目
- 添加新题目
- 导入/导出题库
- 管理待处理题目

## 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PORT | 8001 | 服务端口 |
| API_KEY | - | API 认证密钥（可选） |
| WORKERS | 1 | 工作进程数 |

## 注意事项

1. **端口冲突**: 如果 8001 端口被占用，使用 `PORT=8002` 指定其他端口
2. **数据库位置**: SQLite 数据库文件位于 `tiku/questions.db`
3. **题库备份**: 原始题库数据存储在 `tiku/tiku.json`
4. **跨域访问**: 服务器已配置 CORS，允许所有来源访问

## 停止服务

按 `Ctrl+C` 停止服务器

## 生产环境部署建议

1. 使用 `gunicorn` 或 `uvicorn` 配置多工作进程
2. 配置 Nginx 反向代理
3. 设置防火墙规则
4. 启用 API_KEY 认证
5. 定期备份数据库文件

## 技术栈

- **后端**: Python 3.13, FastAPI, uvicorn, aiosqlite
- **前端**: Vue 3, Element Plus, Vite
- **数据库**: SQLite
- **用户脚本**: Tampermonkey, Vue 3, Pinia

---

部署时间: 2026-09-23
部署状态: ✅ 成功运行

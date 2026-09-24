# 学习通脚本优化总结 v2.1.8

## 实现的三大优化

### 1. ✅ AI重试机制（带指数退避）

**实现方法：**
- 新增 `callAIWithRetry()` 方法
- 默认重试3次，初始延迟1秒
- 指数退避策略：1s → 2s → 4s
- 处理超时、网络错误和无效响应

**配置项：**
- `aiRetryCount`: 重试次数（默认3次）
- `aiRetryDelay`: 初始延迟（默认1000ms）

---

### 2. ✅ 硬编码测试配置

**当前配置（已写死到 defaultConfig$1）：**

```javascript
// 自定义题库
customApiEnabled: true
customApiUrl: "http://localhost:8002/api/search"

// AI答题
aiEnabled: true
aiApiUrl: "https://jiahaoapi.zeabur.app/v1/chat/completions"
aiModel: "deepseek-v4.1-flash"
aiApiKey: "<已移除，请在本地配置>"

// Jev验证
jevEnabled: true
jevApiUrl: "https://api.typesafe.ai/v1/systemone"
jevModel: "jev-latest"
jevApiKey: "<已移除，请在本地配置>"
jevMinConfidence: 0.7
```

---

### 3. ✅ Jev模型集成（答案验证）

**重要发现：**
Jev 不是 LLM，而是 TypeSafe 的 **System One 判断模型**，用于快速评估而非文本生成。

**新架构设计：**

```
┌─────────────────────────────────────────────────────────┐
│                    答题流程                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. 题库查询（本地）                                      │
│     └─ http://localhost:8002/api/search                 │
│                                                          │
│  2. AI生成答案（DeepSeek LLM）                           │
│     └─ 生成候选答案文本                                   │
│                                                          │
│  3. Jev验证（TypeSafe System One）                       │
│     ├─ 评估答案质量（Score: 0-4分）                       │
│     ├─ 评估答案可靠性（Noul: 0-1概率）                    │
│     └─ 综合判断是否采用                                   │
│                                                          │
│  4. 决策                                                 │
│     ├─ Jev验证通过 → 使用答案 ✓                          │
│     ├─ Jev验证未通过 → 拒绝答案 ✗                        │
│     └─ Jev失败 → 使用原答案（降级策略）                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Jev验证逻辑：**

新增 `verifyAnswerWithJev()` 方法，使用两个判断问题：

1. **质量评分（Score）**：
   - 0: 答案明显错误或完全不相关
   - 1: 答案部分正确但有明显缺陷
   - 2: 答案基本正确但不够完整
   - 3: 答案正确且完整
   - 4: 答案非常准确且详尽

2. **可靠性判断（Noul）**：
   - True: 答案逻辑清晰、表述准确、符合常识
   - False: 答案含糊不清、自相矛盾或明显错误

**通过条件：**
```javascript
综合置信度 >= 0.6 && 质量分数 >= 2
```

---

## 技术细节

### TypeSafe API调用格式

```javascript
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "model": "jev-latest",
  "state": {
    "question": "题目内容",
    "questionType": "单选题",
    "answer": ["答案"],
    "options": ["A选项", "B选项", ...]
  },
  "questions": {
    "quality": {
      "type": "score",
      "instructions": "评估这个答案的质量和正确性",
      "criteria": ["等级0", "等级1", ..., "等级4"]
    },
    "confidence": {
      "type": "noul",
      "instructions": "这个答案是否看起来可靠和可信",
      "criteria": {
        "true": "答案逻辑清晰、表述准确、符合常识",
        "false": "答案含糊不清、自相矛盾或明显错误"
      }
    }
  }
}
```

### 响应格式

```javascript
{
  "answers": {
    "quality": {
      "score": 3.2,           // 加权分数
      "confidence": 0.85,     // 置信度
      "probabilities": [...]  // 各等级概率
    },
    "confidence": {
      "noul": 0.92           // 可靠性概率
    }
  }
}
```

---

## 控制台日志示例

```
DeepSeek请求发送中... (尝试 1/3) 模型: deepseek-v4.1-flash
DeepSeek返回结果: {...}
DeepSeek答案解析成功: ["正确"]
Jev验证请求: {...}
Jev验证返回: {...}
Jev验证结果: 质量分=3.20, 质量置信度=0.85, 可靠性=0.92, 综合置信度=0.89
Jev验证通过，使用答案
```

---

## 配置说明

所有配置项都已添加到用户界面：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| aiRetryCount | number | 3 | AI重试次数 |
| aiRetryDelay | number | 1000 | 重试初始延迟（毫秒）|
| jevEnabled | switch | true | 启用Jev验证 |
| jevApiUrl | input | api.typesafe.ai | TypeSafe API地址 |
| jevModel | input | jev-latest | Jev模型名称 |
| jevApiKey | input | apikey_... | TypeSafe API密钥 |
| jevMinConfidence | number | 0.7 | 最低置信度阈值（已硬编码验证逻辑，此配置项暂未使用）|

---

## 变更文件

- `学习通脚本.js` (v2.1.8-optimized)
  - 修改了 `defaultConfig$1`（硬编码测试配置）
  - 新增 `callAIWithRetry()` 方法
  - 新增 `verifyAnswerWithJev()` 方法
  - 保留 `parseAIAnswer()` 辅助方法
  - 重构 `getAnswerFromAI()` 主流程
  - 更新 `@connect` 指令：添加 `api.typesafe.ai`

---

## 使用建议

1. **开发测试阶段**：保持当前硬编码配置，确保环境一致
2. **Jev验证策略**：
   - 低价值题目可关闭Jev（节省成本）
   - 高价值考试建议开启Jev（提高准确率）
3. **降级策略**：Jev失败时自动使用DeepSeek原答案，保证可用性
4. **监控日志**：观察Jev验证通过率，调整阈值参数

---

## 成本考虑

- **DeepSeek**: ~0.1¥/百万tokens（生成答案）
- **TypeSafe Jev**: 查看官网定价（验证评估）

建议：先小规模测试验证效果，再决定是否全量开启Jev。

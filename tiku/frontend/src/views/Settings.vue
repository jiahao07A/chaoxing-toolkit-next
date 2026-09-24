<template>
  <section class="settings-page">
    <div class="page-heading">
      <div>
        <h1>脚本配置</h1>
        <p>版本 {{ version }}，敏感值仅显示掩码</p>
      </div>
      <button class="primary-btn" :disabled="saving" @click="save">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </div>

    <div v-if="loading" class="empty-state">正在读取配置...</div>
    <div v-else class="settings-grid">
      <article v-for="group in groups" :key="group.title" class="settings-section">
        <h2>{{ group.title }}</h2>
        <label v-for="field in group.fields" :key="field.key" class="setting-field">
          <span>{{ field.label }}</span>
          <input
            v-if="field.type !== 'boolean' && field.type !== 'select'"
            v-model="form[field.key]"
            :type="field.type === 'number' ? 'number' : field.secret ? 'password' : 'text'"
            :placeholder="field.secret ? '保持已保存值请勿修改' : ''"
          />
          <select v-else-if="field.type === 'select'" v-model="form[field.key]">
            <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
          <input v-else v-model="form[field.key]" type="checkbox" />
        </label>
      </article>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, updateConfig } from '../api'

const loading = ref(true)
const saving = ref(false)
const version = ref(1)
const form = reactive({})

const fields = [
  ['debugger', '调试模式', 'boolean'],
  ['thtoken', '题库海密钥', 'text', true],
  ['yztoken', '一之题库密钥', 'text', true],
  ['gptKey', 'GPT 密钥', 'text', true],
  ['gptModel', 'GPT 模型', 'text'],
  ['gpt', '启用 GPT 兼容链路', 'boolean'],
  ['gptType', 'GPT 题型范围', 'text'],
  ['customApiEnabled', '启用本地题库', 'boolean'],
  ['customApiUrl', '题库地址', 'text'],
  ['customApiKey', '题库密钥', 'text', true],
  ['questionBankEnabled', '启用全部题库', 'boolean'],
  ['tikuHaiEnabled', '启用题库海', 'boolean'],
  ['yiZhiEnabled', '启用一之题库', 'boolean'],
  ['yanXiEnabled', '启用言溪题库', 'boolean'],
  ['mukeEnabled', '启用 Muke 题库', 'boolean'],
  ['aiEnabled', '启用 AI', 'boolean'],
  ['aiApiUrl', 'AI 地址', 'text'],
  ['aiModel', 'AI 模型', 'text'],
  ['aiApiKey', 'AI 密钥', 'text', true],
  ['aiRetryCount', 'AI 重试次数', 'number'],
  ['aiRetryDelay', 'AI 重试延迟（毫秒）', 'number'],
  ['jevEnabled', '启用 Jev 验证', 'boolean'],
  ['jevApiUrl', 'Jev 地址', 'text'],
  ['jevModel', 'Jev 模型', 'text'],
  ['jevApiKey', 'Jev 密钥', 'text', true],
  ['jevMinConfidence', 'Jev 最低置信度', 'number'],
  ['interval', '通用间隔（秒）', 'number'],
  ['answerIntervalMin', '答题最小间隔（秒）', 'number'],
  ['answerIntervalMax', '答题最大间隔（秒）', 'number'],
  ['submitDelayMin', '提交最小延迟（秒）', 'number'],
  ['submitDelayMax', '提交最大延迟（秒）', 'number'],
  ['autoAnswer', '自动答题', 'boolean'],
  ['autoVideo', '自动视频', 'boolean'],
  ['autoJump', '自动切换', 'boolean'],
  ['autoSubmit', '自动提交', 'boolean'],
  ['autoExam', '考试自动切换', 'boolean'],
  ['hideExam', '隐藏考试提示', 'boolean'],
  ['notice', '脚本公告', 'text'],
  ['deepseekKey', 'DeepSeek 密钥', 'text', true],
  ['deepseekEnabled', '启用 DeepSeek 兼容配置', 'boolean'],
  ['deepseekModel', 'DeepSeek 模型', 'text'],
  ['minAccuracy', '最低正确率', 'number'],
  ['logEnabled', '显示插件日志', 'boolean'],
  ['logLevel', '日志级别', 'select', false, [
    { label: '错误', value: 'error' },
    { label: '警告', value: 'warn' },
    { label: '信息', value: 'info' },
    { label: '调试', value: 'debug' }
  ]],
  ['logShowQuestion', '显示题目内容日志', 'boolean'],
  ['logShowAnswer', '显示答案内容日志', 'boolean'],
  ['logShowRequests', '显示请求过程日志', 'boolean'],
  ['logShowConfig', '显示配置同步日志', 'boolean'],
  ['logShowAi', '显示 AI 日志', 'boolean'],
  ['logShowJev', '显示 Jev 日志', 'boolean'],
  ['logShowLegacy', '显示旧题库日志', 'boolean'],
  ['logShowTiming', '显示耗时日志', 'boolean'],
  ['logShowWarnings', '显示警告日志', 'boolean'],
  ['logShowErrors', '显示错误日志', 'boolean'],
  ['logQuestionPreviewLength', '题目预览长度', 'number'],
  ['logAnswerPreviewLength', '答案预览长度', 'number']
]

const groups = [
  { title: '题库开关', fields: fields.filter(([key]) => ['questionBankEnabled', 'customApiEnabled', 'tikuHaiEnabled', 'yiZhiEnabled', 'yanXiEnabled', 'mukeEnabled', 'customApiUrl', 'customApiKey'].includes(key)).map(toField) },
  { title: 'AI 与验证', fields: fields.filter(([key]) => ['aiEnabled', 'aiApiUrl', 'aiModel', 'aiApiKey', 'aiRetryCount', 'aiRetryDelay', 'jevEnabled', 'jevApiUrl', 'jevModel', 'jevApiKey', 'jevMinConfidence', 'deepseekKey', 'deepseekEnabled', 'deepseekModel', 'gptKey', 'gptModel', 'gpt', 'gptType'].includes(key)).map(toField) },
  { title: '日志显示', fields: fields.filter(([key]) => key.startsWith('log')).map(toField) },
  { title: '脚本行为', fields: fields.filter(([key]) => !['questionBankEnabled', 'customApiEnabled', 'tikuHaiEnabled', 'yiZhiEnabled', 'yanXiEnabled', 'mukeEnabled', 'customApiUrl', 'customApiKey', 'aiEnabled', 'aiApiUrl', 'aiModel', 'aiApiKey', 'aiRetryCount', 'aiRetryDelay', 'jevEnabled', 'jevApiUrl', 'jevModel', 'jevApiKey', 'jevMinConfidence', 'deepseekKey', 'deepseekEnabled', 'deepseekModel', 'gptKey', 'gptModel', 'gpt', 'gptType'].includes(key) && !key.startsWith('log')).map(toField) }
]

function toField([key, label, type, secret, options]) {
  return { key, label, type, secret: Boolean(secret), options }
}

async function load() {
  try {
    const response = await getConfig()
    version.value = response.data.version
    Object.assign(form, response.data.config)
    if (Array.isArray(form.gptType)) form.gptType = form.gptType.join(',')
  } catch (error) {
    ElMessage.error('配置读取失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form }
    if (typeof payload.gptType === 'string') {
      payload.gptType = payload.gptType.split(',').map((item) => item.trim()).filter(Boolean)
    }
    const response = await updateConfig({ version: version.value, config: payload })
    version.value = response.data.version
    Object.assign(form, response.data.config)
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '配置保存失败，请刷新后重试')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('focus', load)
})

onBeforeUnmount(() => window.removeEventListener('focus', load))
</script>

<style scoped>
.settings-page { padding: 28px 32px 48px; }
.page-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-heading h1 { font-family: var(--serif); font-size: 24px; font-weight: 500; }
.page-heading p { margin-top: 6px; color: var(--text-muted); font-size: 12px; }
.primary-btn { border: 0; padding: 10px 20px; background: var(--gold); color: #fff; cursor: pointer; }
.primary-btn:disabled { opacity: .6; cursor: wait; }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.settings-section { padding: 20px; background: var(--bg-card); border: 1px solid var(--border); }
.settings-section h2 { margin-bottom: 16px; font-family: var(--serif); font-size: 16px; font-weight: 500; }
.setting-field { display: grid; grid-template-columns: 1fr 1.25fr; align-items: center; gap: 16px; min-height: 42px; border-top: 1px solid var(--border-light); color: var(--text-secondary); font-size: 13px; }
.setting-field input[type='text'], .setting-field input[type='password'], .setting-field input[type='number'] { width: 100%; height: 32px; padding: 0 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); }
.setting-field select { width: 100%; height: 32px; padding: 0 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); }
.setting-field input[type='checkbox'] { justify-self: start; accent-color: var(--gold); }
@media (max-width: 760px) { .settings-grid { grid-template-columns: 1fr; } .settings-page { padding: 20px 16px 32px; } }
</style>

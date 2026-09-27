<template>
  <section class="settings-page">
    <div class="page-heading">
      <div class="heading-copy">
        <span class="eyebrow">设置中心</span>
        <h1>脚本配置</h1>
        <p>版本 {{ version }} · 敏感值默认掩码显示，修改后记得保存</p>
      </div>
      <div class="heading-actions">
        <span class="save-state" :class="`is-${saveState}`">{{ saveStateLabel }}</span>
        <button class="secondary-btn" type="button" :disabled="loading || saving || !defaultsAvailable" :title="defaultsAvailable ? '恢复服务端默认配置' : '请重启后端后使用默认配置'" @click="resetToDefaults">恢复默认</button>
        <button class="primary-btn" type="button" :disabled="saving || !isDirty" @click="save">{{ saving ? '保存中...' : '保存配置' }}</button>
      </div>
    </div>

    <div v-if="loading" class="empty-state">正在读取配置...</div>
    <template v-else>
      <div class="settings-toolbar">
        <label class="settings-search">
          <span class="sr-only">搜索设置</span>
          <span class="search-icon" aria-hidden="true">⌕</span>
          <input v-model.trim="searchQuery" type="search" placeholder="搜索设置名称或说明" />
          <button v-if="searchQuery" type="button" class="clear-search" title="清除搜索" @click="searchQuery = ''">×</button>
        </label>
        <span class="field-summary">显示 {{ visibleFieldCount }} / {{ totalFieldCount }} 项</span>
      </div>

      <div v-if="filteredGroups.length === 0" class="empty-state settings-empty">
        <strong>没有匹配的设置</strong>
        <span>换个关键词试试，或清除搜索条件。</span>
      </div>
      <div v-else class="settings-grid">
        <article v-for="group in filteredGroups" :key="group.title" class="settings-section">
          <header class="settings-section-header">
            <div>
              <h2>{{ group.title }}</h2>
              <p>{{ group.description }}</p>
            </div>
            <span class="section-count">{{ group.fields.length }} 项</span>
          </header>
          <div class="settings-fields">
            <div v-for="field in group.fields" :key="field.key" class="setting-field">
              <div class="setting-copy">
                <span class="setting-label">
                  {{ field.label }}
                  <em v-if="field.secret" class="secret-mark">敏感</em>
                </span>
                <small>{{ field.description }}</small>
              </div>
              <div class="setting-control">
                <label v-if="field.type === 'boolean'" class="toggle-control">
                  <input v-model="form[field.key]" type="checkbox" />
                  <span class="toggle-track" aria-hidden="true"><span class="toggle-thumb"></span></span>
                  <span class="toggle-label">{{ form[field.key] ? '已开启' : '已关闭' }}</span>
                </label>
                <div v-else-if="field.secret" class="secret-control">
                  <input v-model="form[field.key]" :type="visibleSecrets[field.key] ? 'text' : 'password'" :placeholder="field.placeholder || '保持已保存值请勿修改'" autocomplete="off" />
                  <button type="button" class="input-action" :title="visibleSecrets[field.key] ? '隐藏内容' : '显示内容'" @click="toggleSecret(field.key)">{{ visibleSecrets[field.key] ? '隐藏' : '显示' }}</button>
                </div>
                <select v-else-if="field.type === 'select'" v-model="form[field.key]">
                  <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <input v-else v-model.number="form[field.key]" :type="field.type === 'number' ? 'number' : 'text'" :min="field.minimum" :max="field.maximum" :placeholder="field.placeholder || ''" />
              </div>
            </div>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getConfig, getConfigDefaults, updateConfig } from '../api'
import { GENERATED_CONFIG_FIELDS } from '../generated/config'

const loading = ref(true)
const saving = ref(false)
const version = ref(1)
const searchQuery = ref('')
const saveState = ref('synced')
const form = reactive({})
const savedSnapshot = ref('{}')
const defaultConfig = ref({})
const defaultsAvailable = ref(false)
const visibleSecrets = reactive({})

const groupDescriptions = {
  '自动流程': '控制答题、视频和章节切换等自动行为。',
  '题库与接口': '选择答案来源，并配置本地或第三方题库。',
  'AI 与验证': '配置 AI 答题、模型验证和重试策略。',
  '视频与诊断': '控制视频播放诊断和随机暂停策略。',
  '日志': '控制运行日志的范围和脱敏展示。',
  '高级行为': '较少使用的兼容和调试选项。'
}
const generatedFields = GENERATED_CONFIG_FIELDS.map((field) => ({
  key: field.key,
  label: field.description,
  description: field.description,
  type: field.type === 'integer' ? 'number' : field.type,
  minimum: field.minimum,
  maximum: field.maximum,
  group: field.key === 'videoDiagnosticsEnabled' || field.key.startsWith('randomPause') ? '视频与诊断' : '高级行为'
}))
const field = (key, label, description, type, group, extra = {}) => ({ key, label, description, type, group, ...extra })
const fields = [
  ...generatedFields,
  field('interval', '章节切换间隔（秒）', '脚本处理完当前章节后等待的时间。', 'number', '自动流程'),
  field('answerIntervalMin', '答题最小间隔（秒）', '每道题之间的最小等待时间。', 'number', '自动流程'),
  field('answerIntervalMax', '答题最大间隔（秒）', '每道题之间的最大等待时间。', 'number', '自动流程'),
  field('submitDelayMin', '提交最小延迟（秒）', '全部答完后提交前的最小等待时间。', 'number', '自动流程'),
  field('submitDelayMax', '提交最大延迟（秒）', '全部答完后提交前的最大等待时间。', 'number', '自动流程'),
  field('autoAnswer', '自动答题', '自动处理章节测验、作业和考试题目。', 'boolean', '自动流程'),
  field('autoVideo', '自动视频', '自动播放视频和音频任务。', 'boolean', '自动流程'),
  field('autoJump', '自动切换', '任务完成后自动进入下一章节。', 'boolean', '自动流程'),
  field('autoSubmit', '自动提交', '达到最低正确率后自动提交答案。', 'boolean', '自动流程'),
  field('autoExam', '考试自动切换', '考试中自动切换到下一题。', 'boolean', '自动流程'),
  field('hideExam', '隐藏考试提示', '隐藏考试页面中的辅助提示。', 'boolean', '自动流程'),
  field('minAccuracy', '最低正确率', '低于此比例时不自动提交答案，范围 0-1。', 'number', '自动流程'),
  field('questionBankEnabled', '启用全部题库', '关闭后跳过所有题库，但不影响 AI 答题。', 'boolean', '题库与接口'),
  field('customApiEnabled', '启用本地题库', '优先使用本地题库接口查询答案。', 'boolean', '题库与接口'),
  field('customApiUrl', '题库地址', '本地题库 API 地址，例如 http://localhost:8002/api/search。', 'text', '题库与接口', { dependsOn: 'customApiEnabled' }),
  field('customApiKey', '题库密钥', '本地题库服务要求的 API 密钥。', 'text', '题库与接口', { secret: true, dependsOn: 'customApiEnabled' }),
  field('thtoken', '题库海密钥', '第三方题库海服务的访问密钥。', 'text', '题库与接口', { secret: true }),
  field('yztoken', '一之题库密钥', '第三方一之题库服务的访问密钥。', 'text', '题库与接口', { secret: true }),
  field('tikuHaiEnabled', '启用题库海', '启用题库海旧接口。', 'boolean', '题库与接口', { dependsOn: 'questionBankEnabled' }),
  field('yiZhiEnabled', '启用一之题库', '启用一之题库旧接口。', 'boolean', '题库与接口', { dependsOn: 'questionBankEnabled' }),
  field('yanXiEnabled', '启用言溪题库', '启用言溪题库旧接口。', 'boolean', '题库与接口', { dependsOn: 'questionBankEnabled' }),
  field('mukeEnabled', '启用 Muke 题库', '启用 Muke 题库旧接口。', 'boolean', '题库与接口', { dependsOn: 'questionBankEnabled' }),
  field('aiEnabled', '启用 AI', '题库未命中时，使用 AI 尝试生成答案。', 'boolean', 'AI 与验证'),
  field('aiApiUrl', 'AI 地址', 'OpenAI 兼容的 Chat Completions 地址。', 'text', 'AI 与验证', { dependsOn: 'aiEnabled' }),
  field('aiModel', 'AI 模型', 'AI 接口使用的模型名称。', 'text', 'AI 与验证', { dependsOn: 'aiEnabled' }),
  field('aiApiKey', 'AI 密钥', 'AI 服务的访问密钥。', 'text', 'AI 与验证', { secret: true, dependsOn: 'aiEnabled' }),
  field('aiRetryCount', 'AI 重试次数', '请求失败后的最大重试次数。', 'number', 'AI 与验证', { dependsOn: 'aiEnabled' }),
  field('aiRetryDelay', 'AI 重试延迟（毫秒）', '重试前等待的初始时间。', 'number', 'AI 与验证', { dependsOn: 'aiEnabled' }),
  field('gpt', '启用 GPT 兼容链路', '开启后使用 GPT 兼容接口处理指定题型。', 'boolean', 'AI 与验证'),
  field('gptKey', 'GPT 密钥', 'GPT 兼容接口的访问密钥。', 'text', 'AI 与验证', { secret: true, dependsOn: 'gpt' }),
  field('gptModel', 'GPT 模型', 'GPT 兼容接口使用的模型名称。', 'text', 'AI 与验证', { dependsOn: 'gpt' }),
  field('gptType', 'GPT 题型范围', '填写题型编号，多个编号用逗号分隔，例如 0,1,4。', 'text', 'AI 与验证', { dependsOn: 'gpt' }),
  field('jevEnabled', '启用 Jev 验证', '使用 Jev 模型验证 AI 答案质量。', 'boolean', 'AI 与验证', { dependsOn: 'aiEnabled' }),
  field('jevApiUrl', 'Jev 地址', 'TypeSafe Jev API 地址。', 'text', 'AI 与验证', { dependsOn: 'jevEnabled' }),
  field('jevModel', 'Jev 模型', 'Jev 使用的模型名称。', 'text', 'AI 与验证', { dependsOn: 'jevEnabled' }),
  field('jevApiKey', 'Jev 密钥', 'TypeSafe Jev API 密钥。', 'text', 'AI 与验证', { secret: true, dependsOn: 'jevEnabled' }),
  field('jevMinConfidence', 'Jev 最低置信度', '低于此置信度的答案将被拒绝，范围 0-1。', 'number', 'AI 与验证', { dependsOn: 'jevEnabled' }),
  field('deepseekEnabled', '启用 DeepSeek 兼容配置', '使用独立的 DeepSeek 配置覆盖 AI 设置。', 'boolean', 'AI 与验证'),
  field('deepseekKey', 'DeepSeek 密钥', 'DeepSeek 兼容配置的访问密钥。', 'text', 'AI 与验证', { secret: true, dependsOn: 'deepseekEnabled' }),
  field('deepseekModel', 'DeepSeek 模型', 'DeepSeek 兼容配置使用的模型名称。', 'text', 'AI 与验证', { dependsOn: 'deepseekEnabled' }),
  field('logEnabled', '显示插件日志', '在运行面板中记录插件运行过程。', 'boolean', '日志'),
  field('logLevel', '日志级别', '选择需要显示的最低日志级别。', 'select', '日志', { dependsOn: 'logEnabled', options: [{ label: '错误', value: 'error' }, { label: '警告', value: 'warn' }, { label: '信息', value: 'info' }, { label: '调试', value: 'debug' }] }),
  ...[
    ['logShowQuestion', '显示题目内容日志'], ['logShowAnswer', '显示答案内容日志'], ['logShowRequests', '显示请求过程日志'],
    ['logShowConfig', '显示配置同步日志'], ['logShowAi', '显示 AI 日志'], ['logShowJev', '显示 Jev 日志'],
    ['logShowLegacy', '显示旧题库日志'], ['logShowTiming', '显示耗时日志'], ['logShowWarnings', '显示警告日志'], ['logShowErrors', '显示错误日志']
  ].map(([key, label]) => field(key, label, '按日志类别控制运行面板中显示的内容。', 'boolean', '日志', { dependsOn: 'logEnabled' })),
  field('logQuestionPreviewLength', '题目预览长度', '日志中题目内容的最大显示长度。', 'number', '日志', { dependsOn: 'logEnabled' }),
  field('logAnswerPreviewLength', '答案预览长度', '日志中答案内容的最大显示长度。', 'number', '日志', { dependsOn: 'logEnabled' }),
  field('debugger', '调试模式', '记录更详细的运行信息，排查问题时临时开启。', 'boolean', '高级行为'),
  field('notice', '脚本公告', '在插件运行面板中显示的公告内容。', 'text', '高级行为')
]

const groupOrder = ['自动流程', '题库与接口', 'AI 与验证', '视频与诊断', '日志', '高级行为']
const groups = groupOrder.map((title) => ({ title, description: groupDescriptions[title], fields: fields.filter((item) => item.group === title) }))
const isFieldEnabled = (item) => !item.dependsOn || Boolean(form[item.dependsOn])
const matchesSearch = (item, group, query) => !query || [item.key, item.label, item.description, group.title].some((value) => String(value).toLowerCase().includes(query.toLowerCase()))
const filteredGroups = computed(() => groups.map((group) => ({ ...group, fields: group.fields.filter((item) => isFieldEnabled(item) && matchesSearch(item, group, searchQuery.value)) })).filter((group) => group.fields.length > 0))
const totalFieldCount = fields.length
const visibleFieldCount = computed(() => filteredGroups.value.reduce((total, group) => total + group.fields.length, 0))
const isDirty = computed(() => JSON.stringify(form, Object.keys(form).sort()) !== savedSnapshot.value)
const saveStateLabel = computed(() => ({ synced: '已同步', dirty: '有未保存修改', saving: '正在保存', error: '保存失败' })[saveState.value])

function toggleSecret(key) { visibleSecrets[key] = !visibleSecrets[key] }
function normalizeForServer(value) {
  const payload = { ...value }
  if (typeof payload.gptType === 'string') payload.gptType = payload.gptType.split(',').map((item) => item.trim()).filter(Boolean)
  return payload
}
async function load() {
  loading.value = true
  try {
    const response = await getConfig()
    version.value = response.data.version
    Object.assign(form, response.data.config)
    if (Array.isArray(form.gptType)) form.gptType = form.gptType.join(',')
    try {
      const defaultsResponse = await getConfigDefaults()
      defaultConfig.value = { ...defaultsResponse.data.config }
      if (Array.isArray(defaultConfig.value.gptType)) defaultConfig.value.gptType = defaultConfig.value.gptType.join(',')
      defaultsAvailable.value = true
    } catch (error) {
      defaultConfig.value = { ...form }
      defaultsAvailable.value = false
      ElMessage.warning('默认配置暂不可用，请重启后端后再使用恢复默认')
    }
    savedSnapshot.value = JSON.stringify(form, Object.keys(form).sort())
    saveState.value = 'synced'
  } catch (error) {
    saveState.value = 'error'
    ElMessage.error('配置读取失败，请确认后端已启动')
  } finally { loading.value = false }
}
async function save() {
  if (!isDirty.value) return
  saving.value = true
  saveState.value = 'saving'
  try {
    const response = await updateConfig({ version: version.value, config: normalizeForServer(form) })
    version.value = response.data.version
    Object.assign(form, response.data.config)
    if (Array.isArray(form.gptType)) form.gptType = form.gptType.join(',')
    savedSnapshot.value = JSON.stringify(form, Object.keys(form).sort())
    saveState.value = 'synced'
    ElMessage.success('配置已保存')
  } catch (error) {
    saveState.value = 'error'
    ElMessage.error(error.response?.data?.detail || '配置保存失败，请刷新后重试')
  } finally { saving.value = false }
}
async function resetToDefaults() {
  try {
    await ElMessageBox.confirm('将当前设置恢复为服务端默认值，尚未保存的修改会被覆盖。', '确认恢复默认', { type: 'warning', confirmButtonText: '恢复默认', cancelButtonText: '取消' })
    Object.keys(form).forEach((key) => delete form[key])
    Object.assign(form, { ...defaultConfig.value })
    saveState.value = 'dirty'
    ElMessage.success('已恢复默认值，请点击保存配置使其生效')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('恢复默认失败')
  }
}
watch(isDirty, (dirty) => { if (saveState.value !== 'saving' && saveState.value !== 'error') saveState.value = dirty ? 'dirty' : 'synced' })
onMounted(() => { load(); window.addEventListener('focus', load) })
onBeforeUnmount(() => window.removeEventListener('focus', load))
</script>

<style scoped>
.settings-page { padding: 28px 32px 48px; }
.page-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-bottom: 22px; }
.heading-copy { min-width: 0; }
.eyebrow { display: block; margin-bottom: 6px; color: var(--gold-text); font-size: 11px; letter-spacing: 2px; }
.page-heading h1 { font-family: var(--serif); font-size: 26px; font-weight: 500; }
.page-heading p { margin-top: 7px; color: var(--text-muted); font-size: 12px; }
.heading-actions { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
.save-state { min-width: 92px; color: var(--text-muted); font-size: 12px; text-align: right; }
.save-state.is-dirty { color: var(--gold-text); }
.save-state.is-error { color: var(--danger); }
.primary-btn, .secondary-btn { height: 38px; padding: 0 16px; border: 1px solid var(--border); font-family: var(--sans); font-size: 12px; cursor: pointer; transition: all .2s; }
.primary-btn { border-color: var(--gold); background: var(--gold); color: #fff; }
.secondary-btn { background: var(--bg-card); color: var(--text-secondary); }
.primary-btn:hover, .secondary-btn:hover { border-color: var(--gold-text); }
.primary-btn:disabled, .secondary-btn:disabled { opacity: .5; cursor: not-allowed; }
.settings-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; padding: 12px 14px; border: 1px solid var(--border-light); background: rgba(255, 253, 248, .72); }
.settings-search { display: flex; align-items: center; width: min(440px, 100%); height: 36px; border: 1px solid var(--border); background: var(--bg); }
.search-icon { padding: 0 4px 0 12px; color: var(--gold-text); font-size: 20px; line-height: 1; }
.settings-search input { flex: 1; min-width: 0; height: 100%; padding: 0 8px; border: 0; outline: 0; background: transparent; color: var(--text); font-family: var(--sans); font-size: 13px; }
.clear-search { width: 30px; height: 30px; margin-right: 3px; border: 0; background: transparent; color: var(--text-muted); cursor: pointer; font-size: 18px; }
.field-summary { flex: 0 0 auto; color: var(--text-muted); font-size: 12px; }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: start; }
.settings-section { min-width: 0; overflow: hidden; background: var(--bg-card); border: 1px solid var(--border); }
.settings-section-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 16px 18px 13px; border-bottom: 1px solid var(--border-light); }
.settings-section-header h2 { font-family: var(--serif); font-size: 16px; font-weight: 500; }
.settings-section-header p { margin-top: 5px; color: var(--text-muted); font-size: 11px; line-height: 1.6; }
.section-count { flex: 0 0 auto; padding: 3px 7px; background: var(--gold-dim); color: var(--gold-text); font-size: 11px; }
.settings-fields { padding: 0 18px; }
.setting-field { display: grid; grid-template-columns: minmax(0, 1fr) minmax(150px, 1.15fr); align-items: center; gap: 16px; min-height: 64px; border-bottom: 1px solid var(--border-light); }
.setting-field:last-child { border-bottom: 0; }
.setting-copy { min-width: 0; }
.setting-label { display: flex; align-items: center; gap: 6px; color: var(--text-secondary); font-size: 13px; line-height: 1.45; }
.setting-copy small { display: block; margin-top: 3px; color: var(--text-muted); font-size: 11px; line-height: 1.45; }
.secret-mark { padding: 1px 5px; border: 1px solid var(--border); color: var(--text-muted); font-size: 10px; font-style: normal; }
.setting-control { min-width: 0; }
.setting-control > input, .setting-control > select, .secret-control input { width: 100%; height: 34px; padding: 0 9px; border: 1px solid var(--border); background: var(--bg); color: var(--text); outline: none; font-family: var(--sans); font-size: 12px; }
.setting-control > input:focus, .setting-control > select:focus, .secret-control:focus-within { border-color: var(--gold); }
.secret-control { display: flex; min-width: 0; border: 1px solid var(--border); background: var(--bg); }
.secret-control input { flex: 1; min-width: 0; border: 0; background: transparent; }
.input-action { flex: 0 0 auto; padding: 0 9px; border: 0; border-left: 1px solid var(--border-light); background: transparent; color: var(--gold-text); cursor: pointer; font-size: 11px; }
.toggle-control { display: inline-flex; align-items: center; gap: 8px; min-height: 34px; cursor: pointer; }
.toggle-control input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.toggle-track { position: relative; display: inline-flex; align-items: center; width: 38px; height: 22px; padding: 2px; border-radius: 11px; background: var(--border); transition: background .2s; }
.toggle-thumb { width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.16); transition: transform .2s; }
.toggle-control input:checked + .toggle-track { background: var(--gold); }
.toggle-control input:checked + .toggle-track .toggle-thumb { transform: translateX(16px); }
.toggle-control input:focus-visible + .toggle-track { outline: 2px solid var(--gold); outline-offset: 2px; }
.toggle-label { color: var(--text-muted); font-size: 11px; }
.empty-state { padding: 52px 20px; color: var(--text-muted); text-align: center; }
.settings-empty { display: flex; flex-direction: column; gap: 6px; border: 1px dashed var(--border); }
.settings-empty strong { color: var(--text-secondary); font-size: 14px; font-weight: 500; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 900px) { .settings-grid { grid-template-columns: 1fr; } }
@media (max-width: 680px) {
  .settings-page { padding: 20px 16px 32px; }
  .page-heading { align-items: flex-start; flex-direction: column; gap: 14px; }
  .heading-actions { width: 100%; justify-content: flex-start; }
  .save-state { order: 3; width: 100%; text-align: left; }
  .settings-toolbar { align-items: stretch; flex-direction: column; gap: 8px; }
  .settings-search { width: 100%; }
  .setting-field { grid-template-columns: 1fr; gap: 7px; padding: 13px 0; }
  .setting-control { width: 100%; }
}
</style>

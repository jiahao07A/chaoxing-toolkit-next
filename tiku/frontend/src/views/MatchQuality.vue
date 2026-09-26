<template>
  <section class="quality-page">
    <div class="page-heading">
      <div>
        <h1>匹配质量</h1>
        <p>仅展示最近 7 天的脱敏决策摘要</p>
      </div>
      <button class="primary-btn" :disabled="loading" @click="load">刷新</button>
    </div>

    <div class="filters">
      <label>阶段
        <select v-model="filters.match_stage" @change="resetAndLoad">
          <option value="">全部阶段</option>
          <option value="exact_typed">类型精确</option>
          <option value="contains_typed">类型包含</option>
          <option value="exact">精确</option>
          <option value="contains">包含</option>
          <option value="reverse_contains">反向包含</option>
          <option value="trimmed_contains">去尾空格</option>
          <option value="underscore_normalized">下划线标准化</option>
          <option value="normalized_similarity">标准化相似</option>
          <option value="none">未找到候选</option>
        </select>
      </label>
      <label>状态
        <select v-model="filters.status" @change="resetAndLoad">
          <option value="">全部状态</option>
          <option value="answered">已回答</option>
          <option value="pending">待处理</option>
        </select>
      </label>
      <label>结果
        <select v-model="filters.found" @change="resetAndLoad">
          <option value="">全部结果</option>
          <option value="true">命中</option>
          <option value="false">未命中</option>
        </select>
      </label>
    </div>

    <div v-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="loading" class="empty-state">正在读取审计摘要...</div>
    <div v-else-if="items.length === 0" class="empty-state">暂无匹配记录</div>
    <div v-else class="audit-list">
      <article v-for="item in items" :key="item.id" class="audit-row">
        <div class="audit-main">
          <div class="audit-title">
            <strong>{{ item.found ? '已命中' : '未命中' }}</strong>
            <span class="stage">{{ item.match_stage }}</span>
            <span>{{ item.status }}</span>
          </div>
          <div class="audit-meta">
            <span>请求 {{ item.request_digest }}</span>
            <span>规范化题干（脱敏） {{ item.normalized_question_preview || '-' }}</span>
            <span>题型 {{ item.question_type || '未提供' }}</span>
            <span>选项 {{ item.option_count }}</span>
            <span>{{ item.duration_ms }} ms</span>
            <time>{{ formatTime(item.created_at) }}</time>
          </div>
          <div v-if="item.failure_reason" class="failure">原因：{{ item.failure_reason }}</div>
        </div>
        <div class="candidate-count">候选 {{ item.candidate_count }}</div>
        <div v-if="item.candidate_summaries?.length" class="candidate-list">
          <span v-for="candidate in item.candidate_summaries" :key="`${item.id}-${candidate.rank}`">
            #{{ candidate.rank }} {{ candidate.score.toFixed(2) }}
          </span>
        </div>
      </article>
    </div>

    <div v-if="total > pageSize" class="pager">
      <button class="pg-btn" :disabled="page <= 1 || loading" @click="page--; load()">上一页</button>
      <span class="pg-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button class="pg-btn" :disabled="page >= Math.ceil(total / pageSize) || loading" @click="page++; load()">下一页</button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getDecisionAudits } from '../api'

const page = ref(1)
const pageSize = 20
const total = ref(0)
const items = ref([])
const loading = ref(false)
const error = ref('')
const filters = reactive({ match_stage: '', status: '', found: '' })

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filters.match_stage) params.match_stage = filters.match_stage
    if (filters.status) params.status = filters.status
    if (filters.found) params.found = filters.found
    const response = await getDecisionAudits(params)
    if (response.code !== 1) throw new Error('匹配质量读取失败')
    items.value = response.data.items
    total.value = response.data.total
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || requestError.message || '匹配质量读取失败'
  } finally {
    loading.value = false
  }
}

const resetAndLoad = () => {
  page.value = 1
  load()
}

const formatTime = (value) => value ? new Date(value).toLocaleString() : ''

onMounted(load)
</script>

<style scoped>
.quality-page { padding: 28px 32px 48px; }
.page-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-heading h1 { font-family: var(--serif); font-size: 24px; font-weight: 500; }
.page-heading p { margin-top: 6px; color: var(--text-muted); font-size: 12px; }
.primary-btn { border: 0; padding: 10px 20px; background: var(--gold); color: #fff; cursor: pointer; }
.primary-btn:disabled { opacity: .6; cursor: wait; }
.filters { display: flex; gap: 12px; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid var(--border); }
.filters label { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 13px; }
.filters select { height: 32px; min-width: 120px; border: 1px solid var(--border); background: var(--bg); color: var(--text); padding: 0 8px; }
.audit-list { display: grid; gap: 10px; }
.audit-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px 18px; padding: 16px; border: 1px solid var(--border); background: var(--bg-card); }
.audit-title { display: flex; align-items: center; gap: 10px; color: var(--text-secondary); font-size: 13px; }
.audit-title strong { color: var(--text); }
.stage { color: var(--gold); }
.audit-meta { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; color: var(--text-muted); font-size: 12px; }
.failure { margin-top: 8px; color: #a34d42; font-size: 12px; }
.candidate-count { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.candidate-list { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 6px; color: var(--text-muted); font-size: 12px; }
.candidate-list span { padding: 3px 7px; border: 1px solid var(--border-light); }
.empty-state, .error-state { padding: 48px 0; text-align: center; color: var(--text-muted); }
.error-state { color: #a34d42; }
.pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 20px; }
.pg-btn { border: 1px solid var(--border); background: var(--bg-card); color: var(--text-secondary); padding: 7px 12px; cursor: pointer; }
.pg-btn:disabled { opacity: .5; cursor: default; }
.pg-info { color: var(--text-muted); font-size: 12px; }
@media (max-width: 760px) { .quality-page { padding: 20px 16px 32px; } .filters { flex-wrap: wrap; } .audit-row { grid-template-columns: 1fr; } }
</style>

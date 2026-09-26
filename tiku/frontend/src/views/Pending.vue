<template>
  <div class="pending-view">
    <div class="toolbar">
      <input class="search-input" placeholder="搜索待处理题目..." v-model="searchText" @input="debounceSearch" />
      <div class="sort-actions">
        <button class="tool-btn" :class="{ primary: sortBy === 'count' }" @click="changeSort('count')">按搜索次数</button>
        <button class="tool-btn" :class="{ primary: sortBy === 'time' }" @click="changeSort('time')">按时间</button>
        <button class="tool-btn" :class="{ primary: sortBy === 'time_asc' }" @click="changeSort('time_asc')">按时间正序</button>
      </div>
      <button class="tool-btn" @click="openHistory">操作历史</button>
    </div>

    <div v-if="!loadError && !loading && list.length > 0" class="pending-bulkbar">
      <label class="select-all">
        <input type="checkbox" :checked="allSelected" :indeterminate.prop="isIndeterminate" @change="setAllSelected($event.target.checked)" />
        <span>当前页全选</span>
      </label>
      <span class="pending-total">共 {{ total }} 条，当前页 {{ list.length }} 条</span>
      <span v-if="selectedIds.length" class="selected-count">已选 {{ selectedIds.length }} 条</span>
      <div class="bulk-actions">
        <button class="tool-btn primary" :disabled="selectedIds.length === 0" @click="openBatchPromote">批量转正</button>
        <button class="tool-btn danger-btn" :disabled="selectedIds.length === 0" @click="batchDelete">批量删除</button>
      </div>
    </div>

    <div v-if="loadError" class="empty error-state">
      <div class="empty-icon">!</div>
      <div class="empty-text">{{ loadError }}</div>
      <button class="tool-btn primary retry-btn" @click="loadPending">重新加载</button>
    </div>
    <div v-else-if="loading" class="empty"><div class="empty-text">正在加载...</div></div>
    <div v-else-if="list.length === 0" class="empty">
      <div class="empty-icon">净</div><div class="empty-text">暂无待处理题目</div>
    </div>

    <div v-else class="card-list">
      <div v-for="p in list" :key="p.id" class="pending-row">
        <label class="row-checkbox" :title="`选择题目 #${p.id}`">
          <input type="checkbox" :checked="isSelected(p.id)" @change="toggleSelect(p.id)" />
        </label>
        <div class="pending-card-wrap">
          <div v-if="p.duplicate" class="duplicate-notice">
            重复提示：{{ p.duplicate_in_questions ? '题库中已有相同题目' : '待处理列表中存在相同题目' }}
            <span v-if="p.duplicate_ids && p.duplicate_ids.length">（关联 ID：{{ p.duplicate_ids.join('、') }}）</span>
          </div>
          <PendingCard :question="p" @convert="convertToQuestion" @delete="deleteItem" />
        </div>
      </div>
    </div>

    <div v-if="!loadError && total > 0" class="pager">
      <button class="pg-btn" :disabled="page <= 1 || loading" @click="goToPage(page - 1)">上一页</button>
      <span class="pg-info">第 {{ page }} / {{ pageCount }} 页，共 {{ total }} 条</span>
      <button class="pg-btn" :disabled="page >= pageCount || loading" @click="goToPage(page + 1)">下一页</button>
    </div>

    <QuestionForm v-model:visible="formVisible" :question="formQuestion" @saved="onSaved" />

    <el-dialog v-model="batchPromoteVisible" title="批量转正" width="680px" :close-on-click-modal="false">
      <div class="deco-line"></div>
      <p class="dialog-hint">请为选中的每道题填写答案，题目和选项将按当前待处理内容转入题库。</p>
      <div class="batch-promote-list">
        <div v-for="item in batchForms" :key="item.id" class="batch-promote-item">
          <div class="batch-promote-title">#{{ item.id }} · {{ item.question }}</div>
          <div v-if="item.options && item.options.length" class="batch-promote-options">选项：{{ item.options.join(' / ') }}</div>
          <el-input v-model="item.answer" type="textarea" :rows="2" placeholder="请输入答案" />
        </div>
      </div>
      <template #footer>
        <button class="dlg-btn cancel" @click="batchPromoteVisible = false">取消</button>
        <button class="dlg-btn confirm" :disabled="batchPromoteSubmitting" @click="submitBatchPromote">{{ batchPromoteSubmitting ? '提交中...' : '确认转正' }}</button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyVisible" title="待处理操作历史" width="900px" :close-on-click-modal="false">
      <div v-if="historyError" class="history-error">{{ historyError }}</div>
      <div v-else-if="historyLoading" class="history-loading">正在加载历史...</div>
      <el-table v-else :data="historyItems" stripe class="history-table">
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="操作" width="90"><template #default="scope">{{ operationLabel(scope.row.operation) }}</template></el-table-column>
        <el-table-column label="结果" width="110"><template #default="scope">{{ resultLabel(scope.row.result) }}</template></el-table-column>
        <el-table-column label="数量" width="180"><template #default="scope">{{ scope.row.success }} 成功 / {{ scope.row.skipped }} 跳过 / {{ scope.row.failed }} 失败</template></el-table-column>
        <el-table-column prop="failure_reason" label="失败原因" min-width="150" show-overflow-tooltip />
        <el-table-column label="明细" min-width="220" show-overflow-tooltip><template #default="scope">{{ formatHistoryDetails(scope.row.details) }}</template></el-table-column>
      </el-table>
      <div v-if="historyTotal > 0" class="pager history-pager">
        <button class="pg-btn" :disabled="historyPage <= 1 || historyLoading" @click="loadHistory(historyPage - 1)">上一页</button>
        <span class="pg-info">第 {{ historyPage }} / {{ historyPageCount }} 页，共 {{ historyTotal }} 条</span>
        <button class="pg-btn" :disabled="historyPage >= historyPageCount || historyLoading" @click="loadHistory(historyPage + 1)">下一页</button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchDeletePending, batchPromotePending, deletePending, getPending, getPendingHistory } from '../api'
import PendingCard from '../components/PendingCard.vue'
import QuestionForm from '../components/QuestionForm.vue'

const pageSize = 20
const list = ref([])
const total = ref(0)
const page = ref(1)
const searchText = ref('')
const sortBy = ref('count')
const selectedIds = ref([])
const loading = ref(false)
const loadError = ref('')
const formVisible = ref(false)
const formQuestion = ref(null)
const batchPromoteVisible = ref(false)
const batchPromoteSubmitting = ref(false)
const batchForms = ref([])
const historyVisible = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const historyItems = ref([])
const historyPage = ref(1)
const historyTotal = ref(0)
const historyPageSize = 20

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const historyPageCount = computed(() => Math.max(1, Math.ceil(historyTotal.value / historyPageSize)))
const allSelected = computed(() => list.value.length > 0 && list.value.every(item => selectedIds.value.includes(item.id)))
const isIndeterminate = computed(() => selectedIds.value.length > 0 && !allSelected.value)
const getErrorMessage = (error, fallback) => error?.response?.data?.detail || error?.response?.data?.msg || error?.message || fallback

const loadPending = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const params = { page: page.value, page_size: pageSize, sort: sortBy.value }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const res = await getPending(params)
    if (res.code !== 1) throw new Error(res.msg || '加载待处理题目失败')
    list.value = res.items || res.data || []
    total.value = Number(res.total || 0)
    selectedIds.value = selectedIds.value.filter(id => list.value.some(item => item.id === id))
  } catch (error) {
    list.value = []; total.value = 0; loadError.value = getErrorMessage(error, '加载待处理题目失败，请稍后重试')
  } finally { loading.value = false }
}

let timer = null
const debounceSearch = () => {
  clearTimeout(timer)
  timer = setTimeout(() => { page.value = 1; selectedIds.value = []; loadPending() }, 300)
}
const changeSort = (sort) => {
  if (sortBy.value === sort) return
  sortBy.value = sort; page.value = 1; selectedIds.value = []; loadPending()
}
const goToPage = (nextPage) => {
  page.value = Math.min(Math.max(1, nextPage), pageCount.value); selectedIds.value = []; loadPending()
}

const isSelected = (id) => selectedIds.value.includes(id)
const toggleSelect = (id) => { selectedIds.value = isSelected(id) ? selectedIds.value.filter(item => item !== id) : [...selectedIds.value, id] }
const setAllSelected = (checked) => {
  const currentPageIds = list.value.map(item => item.id)
  selectedIds.value = checked ? Array.from(new Set([...selectedIds.value, ...currentPageIds])) : selectedIds.value.filter(id => !currentPageIds.includes(id))
}

const convertToQuestion = (pending) => {
  if (pending.duplicate) ElMessage.warning('该题目存在重复提示，请确认后再转正')
  formQuestion.value = { question: pending.question, type: pending.type, options: [...(pending.options || [])], answer: pending.answer || '', _pendingId: pending.id }
  formVisible.value = true
}
const deleteItem = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这条待处理题目？删除后无法恢复。', '确认删除', { type: 'warning' })
    const res = await deletePending(id)
    if (res.code !== 1) throw new Error(res.msg || '删除失败')
    selectedIds.value = selectedIds.value.filter(item => item !== id); ElMessage.success('已删除')
    if (list.value.length === 1 && page.value > 1) page.value -= 1
    await loadPending()
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error, '删除失败')) }
}
const onSaved = () => { selectedIds.value = []; loadPending() }

const openBatchPromote = () => {
  const selected = list.value.filter(item => selectedIds.value.includes(item.id))
  if (!selected.length) return ElMessage.warning('请先选择要转正的题目')
  batchForms.value = selected.map(item => ({ id: item.id, question: item.question, type: item.type, options: [...(item.options || [])], answer: item.answer || '', duplicate: item.duplicate }))
  batchPromoteVisible.value = true
}
const showBatchResult = async (result, actionLabel) => {
  const details = (result.details || []).map(item => `#${item.id}：${item.status === 'success' ? '成功' : item.status === 'skipped' ? '跳过' : '失败'}${item.reason ? `（${item.reason}）` : ''}`)
  const summary = `${actionLabel}完成：${result.success || 0} 成功，${result.skipped || 0} 跳过，${result.failed || 0} 失败${details.length ? `\n\n${details.join('\n')}` : ''}`
  await ElMessageBox.alert(summary, '批量操作结果', { type: result.failed || result.skipped ? 'warning' : 'success', confirmButtonText: '知道了' })
}
const batchDelete = async () => {
  if (!selectedIds.value.length) return ElMessage.warning('请先选择要删除的题目')
  try {
    await ElMessageBox.confirm(`确定删除当前选中的 ${selectedIds.value.length} 条待处理题目？删除后无法恢复。`, '确认批量删除', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    const res = await batchDeletePending(selectedIds.value, true)
    if (res.code !== 1) throw new Error(res.msg || '批量删除失败')
    const result = res.data || {}; selectedIds.value = []
    await showBatchResult(result, '批量删除')
    if (page.value > 1 && Number(result.success || 0) >= list.value.length) page.value -= 1
    await loadPending()
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error, '批量删除失败')) }
}
const submitBatchPromote = async () => {
  const invalid = batchForms.value.filter(item => !item.answer || !item.answer.trim())
  if (invalid.length) return ElMessage.warning(`请填写 ${invalid.length} 道题的答案`)
  const duplicateCount = batchForms.value.filter(item => item.duplicate).length
  try {
    const warning = duplicateCount ? `选中的题目中有 ${duplicateCount} 条存在重复提示，仍要批量转正吗？` : `确定将选中的 ${batchForms.value.length} 条题目转入题库吗？`
    await ElMessageBox.confirm(warning, '确认批量转正', { type: duplicateCount ? 'warning' : 'info' })
    batchPromoteSubmitting.value = true
    const res = await batchPromotePending(batchForms.value.map(item => ({ id: item.id, question: item.question.trim(), type: item.type, options: (item.options || []).filter(option => option && option.trim()), answer: item.answer.trim() })))
    if (res.code !== 1) throw new Error(res.msg || '批量转正失败')
    batchPromoteVisible.value = false; selectedIds.value = []
    await showBatchResult(res.data || {}, '批量转正'); await loadPending()
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error, '批量转正失败')) }
  finally { batchPromoteSubmitting.value = false }
}

const operationLabel = (operation) => ({ delete: '删除', promote: '转正' }[operation] || operation || '-')
const resultLabel = (result) => ({ success: '全部成功', partial: '部分成功', skipped: '已跳过', failed: '失败' }[result] || result || '-')
const formatHistoryDetails = (details) => (details || []).map(item => `#${item.id} ${item.status === 'success' ? '成功' : item.status === 'skipped' ? '跳过' : '失败'}`).join('，') || '-'
const loadHistory = async (nextPage = 1) => {
  historyLoading.value = true; historyError.value = ''
  try {
    const res = await getPendingHistory({ page: nextPage, page_size: historyPageSize })
    if (res.code !== 1) throw new Error(res.msg || '加载操作历史失败')
    const payload = res.items ? res : (res.data || {})
    historyItems.value = payload.items || []; historyTotal.value = Number(payload.total || 0); historyPage.value = Number(payload.page || nextPage)
  } catch (error) { historyItems.value = []; historyTotal.value = 0; historyError.value = getErrorMessage(error, '加载操作历史失败，请稍后重试') }
  finally { historyLoading.value = false }
}
const openHistory = async () => { historyVisible.value = true; await loadHistory(1) }

onMounted(loadPending)
</script>

<style scoped>
.sort-actions { display: flex; gap: 4px; }
.pending-bulkbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; padding: 10px 14px; background: var(--bg-card); border: 1px solid var(--border-light); font-family: var(--serif); font-size: 12px; color: var(--text-secondary); }
.select-all, .row-checkbox { display: inline-flex; align-items: center; gap: 7px; cursor: pointer; }
.select-all input, .row-checkbox input { accent-color: var(--gold); width: 16px; height: 16px; cursor: pointer; }
.pending-total { color: var(--text-muted); }
.selected-count { color: var(--gold-text); }
.bulk-actions { display: flex; gap: 8px; margin-left: auto; }
.tool-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.danger-btn { color: var(--danger); }
.pending-row { display: flex; align-items: flex-start; gap: 10px; }
.row-checkbox { padding: 22px 0 0 4px; flex-shrink: 0; }
.pending-card-wrap { flex: 1; min-width: 0; }
.duplicate-notice { padding: 7px 12px; background: var(--danger-dim); border: 1px solid rgba(192, 57, 43, 0.2); color: var(--danger); font-family: var(--serif); font-size: 12px; margin-bottom: 6px; }
.retry-btn { margin-top: 16px; }
.dialog-hint, .history-loading, .history-error { font-family: var(--serif); font-size: 13px; color: var(--text-secondary); line-height: 1.7; }
.history-error { color: var(--danger); padding: 20px 0; }
.batch-promote-list { max-height: 460px; overflow-y: auto; padding-right: 4px; }
.batch-promote-item { padding: 12px 0; border-bottom: 1px solid var(--border-light); }
.batch-promote-item:last-child { border-bottom: none; }
.batch-promote-title { font-family: var(--serif); font-size: 13px; line-height: 1.6; color: var(--text); margin-bottom: 5px; }
.batch-promote-options { font-family: var(--serif); font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
.history-table { width: 100%; }
.history-pager { margin-bottom: 0; }
@media (max-width: 760px) {
  .toolbar { flex-wrap: wrap; }
  .search-input { width: 100%; }
  .sort-actions { width: 100%; overflow-x: auto; }
  .bulk-actions { margin-left: 0; width: 100%; }
  .bulk-actions .tool-btn { flex: 1; }
  .pending-row { gap: 6px; }
  .row-checkbox { padding-left: 0; }
}
</style>

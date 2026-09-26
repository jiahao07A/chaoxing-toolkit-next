<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="安全导入题库"
    width="560px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <div class="deco-line"></div>
    <div class="upload-zone" @click="$refs.fileInput.click()" @dragover.prevent @drop.prevent="handleDrop">
      <div class="upload-mark">↑</div>
      <p>{{ file?.name || '选择或拖入 JSON 文件' }}</p>
      <p class="upload-note">最大 10 MB</p>
    </div>
    <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="handleSelect" />

    <div v-if="loading" class="import-state">正在检查文件…</div>
    <template v-if="report">
      <div class="import-summary">
        <span>记录 {{ report.total }}</span>
        <span class="ok">新增 {{ report.new }}</span>
        <span>更新 {{ report.updated }}</span>
        <span>跳过 {{ report.skipped }}</span>
      </div>
      <el-alert v-if="report.can_commit" title="预检通过" type="success" :closable="false" />
      <el-alert v-else title="存在问题，不能提交" type="error" :closable="false" />
      <div v-if="report.errors.length || report.conflicts.length" class="import-issues">
        <div v-for="issue in report.errors" :key="`e-${issue.line}-${issue.code}`" class="issue-row">
          <strong>第 {{ issue.line }} 条</strong><span>{{ issue.message }}</span>
        </div>
        <div v-for="issue in report.conflicts" :key="`c-${issue.line}-${issue.code}`" class="issue-row conflict">
          <strong>第 {{ issue.line }} 条</strong><span>{{ issue.message }}</span>
        </div>
      </div>
    </template>

    <template #footer>
      <button class="dlg-btn cancel" @click="$emit('update:visible', false)">取消</button>
      <button class="dlg-btn confirm" :disabled="!report?.can_commit || loading || committing" @click="doImport">
        {{ committing ? '正在导入…' : '确认合并导入' }}
      </button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { commitImportJson, previewImportJson } from '../api'

defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible', 'imported'])

const file = ref(null)
const report = ref(null)
const loading = ref(false)
const committing = ref(false)

const reset = () => {
  file.value = null
  report.value = null
  loading.value = false
  committing.value = false
}

const checkFile = async (selected) => {
  if (selected.size > 10 * 1024 * 1024) {
    ElMessage.error('文件超过 10 MB')
    return
  }
  file.value = selected
  report.value = null
  loading.value = true
  const formData = new FormData()
  formData.append('file', selected)
  try {
    const response = await previewImportJson(formData)
    report.value = response.data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '文件预检失败')
  } finally {
    loading.value = false
  }
}

const handleSelect = (event) => {
  const selected = event.target.files?.[0]
  if (selected) checkFile(selected)
  event.target.value = ''
}

const handleDrop = (event) => {
  const selected = event.dataTransfer.files?.[0]
  if (selected) checkFile(selected)
}

const doImport = async () => {
  if (!report.value?.can_commit || !report.value.run_id) return
  committing.value = true
  try {
    const response = await commitImportJson(report.value.run_id)
    ElMessage.success(`导入完成：新增 ${response.data.added} 道，跳过 ${response.data.skipped} 道`)
    emit('update:visible', false)
    emit('imported')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '导入提交失败，请重新预检')
  } finally {
    committing.value = false
  }
}

watch(() => file.value, () => { report.value = null })
</script>

<style scoped>
.upload-mark { color: var(--text-muted); font-size: 30px; line-height: 1; }
.upload-note { margin-top: 4px; color: var(--text-muted); font-size: 12px; }
.import-summary { display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0 12px; font-size: 13px; }
.import-summary .ok { color: var(--success, #23855b); }
.import-state { padding: 20px 0; color: var(--text-muted); text-align: center; }
.import-issues { max-height: 180px; overflow: auto; margin-top: 12px; border-top: 1px solid var(--border-color, #ddd); }
.issue-row { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border-color, #ddd); font-size: 12px; }
.issue-row strong { flex: 0 0 auto; }
.issue-row.conflict { color: var(--danger, #c43d3d); }
</style>

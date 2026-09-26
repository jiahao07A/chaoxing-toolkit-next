<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="题库备份"
    width="680px"
    @opened="loadBackups"
  >
    <div v-if="loading" class="backup-state">正在加载…</div>
    <el-empty v-else-if="backups.length === 0" description="暂无备份" />
    <el-table v-else :data="backups" size="small" max-height="360">
      <el-table-column prop="created_at" label="备份时间" min-width="180" />
      <el-table-column prop="row_count" label="题目数" width="90" />
      <el-table-column label="校验摘要" min-width="160">
        <template #default="scope">{{ scope.row.sha256.slice(0, 16) }}…</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="scope">
          <el-button link type="danger" @click="restore(scope.row)">恢复</el-button>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <button class="dlg-btn cancel" @click="$emit('update:visible', false)">关闭</button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getImportBackups, restoreImportBackup } from '../api'

defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible', 'restored'])
const backups = ref([])
const loading = ref(false)

const loadBackups = async () => {
  loading.value = true
  try {
    const response = await getImportBackups()
    backups.value = response.data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '备份列表加载失败')
  } finally {
    loading.value = false
  }
}

const restore = async (backup) => {
  try {
    await ElMessageBox.confirm(
      `将题库恢复到 ${backup.created_at} 时的 ${backup.row_count} 道题。当前题库会被替换，待处理题目不会改变。`,
      '确认恢复备份',
      { type: 'warning', confirmButtonText: '恢复题库', cancelButtonText: '取消' },
    )
    const response = await restoreImportBackup(backup.id)
    ElMessage.success(`已恢复 ${response.data.restored} 道题目`)
    emit('restored')
    emit('update:visible', false)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '恢复失败')
    }
  }
}
</script>

<style scoped>
.backup-state { padding: 28px 0; color: var(--text-muted); text-align: center; }
</style>

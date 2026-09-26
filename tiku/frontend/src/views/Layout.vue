<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-left">
        <span class="header-logo">題庫</span>
        <span class="header-sep"></span>
        <span class="header-label">管理面板</span>
      </div>
      <div class="header-right">
        <div class="stat-item clickable" @click="$router.push('/questions')">
          <span class="stat-label">题库</span>
          <span class="stat-num">{{ stats.total }}</span>
        </div>
        <div class="stat-item clickable" @click="$router.push('/pending')">
          <span class="stat-label">待处理</span>
          <span class="stat-num">{{ stats.pending }}</span>
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="tab-bar">
        <div
          class="tab-item"
          :class="{ active: $route.path === '/questions' }"
          @click="$router.push('/questions')"
        >题库管理</div>
        <div
          class="tab-item"
          :class="{ active: $route.path === '/pending' }"
          @click="$router.push('/pending')"
        >
          待处理题目
          <span v-if="stats.pending > 0" class="tab-badge">{{ stats.pending }}</span>
        </div>
        <div
          class="tab-item"
          :class="{ active: $route.path === '/settings' }"
          @click="$router.push('/settings')"
        >配置</div>
        <div
          class="tab-item"
          :class="{ active: $route.path === '/match-quality' }"
          @click="$router.push('/match-quality')"
        >匹配质量</div>
      </div>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStats } from '../api'

const stats = ref({ total: 0, pending: 0 })

const loadStats = async () => {
  try {
    const res = await getStats()
    if (res.code === 1) stats.value = res.data
  } catch (e) {}
}

onMounted(loadStats)

defineExpose({ loadStats })
</script>

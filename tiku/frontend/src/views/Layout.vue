<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-left">
        <span class="header-logo" aria-label="题库管理">题库</span>
        <span class="header-sep"></span>
        <div>
          <span class="header-label">管理面板</span>
          <span class="header-subtitle">本地题库与脚本配置</span>
        </div>
      </div>
      <div class="header-right">
        <button class="stat-item clickable" type="button" @click="$router.push('/questions')">
          <span class="stat-label">题库</span>
          <span class="stat-num">{{ stats.total }}</span>
        </button>
        <button class="stat-item clickable" type="button" @click="$router.push('/pending')">
          <span class="stat-label">待处理</span>
          <span class="stat-num">{{ stats.pending }}</span>
        </button>
      </div>
    </header>

    <main class="app-main">
      <nav class="tab-bar" aria-label="管理页面">
        <button type="button" class="tab-item" :class="{ active: $route.path === '/questions' }" :aria-current="$route.path === '/questions' ? 'page' : undefined" @click="$router.push('/questions')">题库管理</button>
        <button type="button" class="tab-item" :class="{ active: $route.path === '/pending' }" :aria-current="$route.path === '/pending' ? 'page' : undefined" @click="$router.push('/pending')">
          待处理题目
          <span v-if="stats.pending > 0" class="tab-badge" :aria-label="`${stats.pending} 道待处理题目`">{{ stats.pending }}</span>
        </button>
        <button type="button" class="tab-item" :class="{ active: $route.path === '/settings' }" :aria-current="$route.path === '/settings' ? 'page' : undefined" @click="$router.push('/settings')">配置</button>
        <button type="button" class="tab-item" :class="{ active: $route.path === '/match-quality' }" :aria-current="$route.path === '/match-quality' ? 'page' : undefined" @click="$router.push('/match-quality')">匹配质量</button>
      </nav>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getStats } from '../api'

const stats = ref({ total: 0, pending: 0 })

const loadStats = async () => {
  try {
    const response = await getStats()
    if (response.code === 1) stats.value = response.data
  } catch (error) {
    // 统计请求失败时仍保留页面操作能力。
  }
}

onMounted(loadStats)
defineExpose({ loadStats })
</script>

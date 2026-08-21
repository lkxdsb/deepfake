import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/services/api'
import type { HealthStatus } from '@/types/api'

export const useSystemStore = defineStore('system', () => {
  const health = ref<HealthStatus | null>(null)
  const checking = ref(false)
  const sidebarOpen = ref(false)

  const algorithmReady = computed(() => health.value?.status === 'ok')

  async function refreshHealth() {
    checking.value = true
    try {
      health.value = await api.health()
    } catch (error) {
      health.value = { status: 'unavailable', message: error instanceof Error ? error.message : '服务不可用' }
    } finally {
      checking.value = false
    }
  }

  return { health, checking, sidebarOpen, algorithmReady, refreshHealth }
})

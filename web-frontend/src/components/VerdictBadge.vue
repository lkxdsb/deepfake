<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ label: string; score?: number; compact?: boolean }>()
const isFake = computed(() => props.label?.toLowerCase() === 'fake')
const text = computed(() => (isFake.value ? '疑似伪造' : '倾向真实'))
</script>

<template>
  <span class="verdict-badge" :class="{ fake: isFake, compact }">
    <i />{{ text }}<b v-if="score !== undefined">{{ (score * 100).toFixed(1) }}%</b>
  </span>
</template>

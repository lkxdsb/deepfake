<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number; showLabel?: boolean }>()
const normalized = computed(() => Math.max(0, Math.min(1, Number(props.value) || 0)))
</script>

<template>
  <div class="risk-bar-wrap">
    <div class="risk-bar"><i :style="{ width: `${normalized * 100}%` }" /></div>
    <span v-if="showLabel">{{ (normalized * 100).toFixed(1) }}%</span>
  </div>
</template>

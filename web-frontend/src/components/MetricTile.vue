<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  hint?: string
  tone?: 'default' | 'danger' | 'success' | 'blue'
}>()
</script>

<template>
  <div class="metric-tile" :class="`tone-${tone ?? 'default'}`">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
    <small v-if="hint">{{ hint }}</small>
  </div>
</template>

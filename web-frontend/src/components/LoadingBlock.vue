<script setup lang="ts">
defineProps<{ label?: string }>()
</script>

<template>
  <div class="loading-block" role="status">
    <span class="loader" />
    <p>{{ label ?? '正在加载数据' }}</p>
  </div>
</template>

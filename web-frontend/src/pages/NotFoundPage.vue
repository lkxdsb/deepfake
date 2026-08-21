<script setup lang="ts">
import { ArrowLeft, FileQuestion } from 'lucide-vue-next'
</script>

<template>
  <div class="not-found-page"><FileQuestion :size="36" /><span class="eyebrow">404 · NOT FOUND</span><h2>页面不存在</h2><p>该地址可能已更改，返回检测工作台继续操作。</p><RouterLink class="button button-primary" to="/"><ArrowLeft :size="17" />返回工作台</RouterLink></div>
</template>

<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

defineProps<{ title: string; description: string }>()
</script>

<template>
  <div class="empty-state">
    <Inbox :size="30" />
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>

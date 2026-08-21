<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
onMounted(() => { document.body.className = 'page-welcome' })
onUnmounted(() => { document.body.className = 'theme-containers-b page-default' })
</script>

<template>
  <main class="welcome-shell">
    <section class="welcome-copy">
      <p class="welcome-kicker">Deepfake Forensics System</p><h1>灵眸鉴真</h1>
      <div class="welcome-intro"><p class="welcome-intro__title">平台简介</p><p class="welcome-lede">基于 CASE + Bi-ST 与 XLS-R-2B 的图像、视频、音频一体化深伪检测系统，支持统一检测、可解释证据输出与历史结果复盘。</p></div>
      <div class="welcome-actions"><RouterLink class="button button--primary welcome-cta" to="/">快速开始</RouterLink></div>
    </section>
    <section class="welcome-visual" aria-hidden="true">
      <img src="/static/images/heatmap.webp" alt="" /><div class="welcome-pixel-field" /><div class="welcome-rings" />
      <div class="welcome-beam welcome-beam--one" /><div class="welcome-beam welcome-beam--two" />
      <div class="welcome-shapes"><span class="welcome-shape welcome-shape--a" /><span class="welcome-shape welcome-shape--b" /><span class="welcome-shape welcome-shape--c" /><span class="welcome-shape welcome-shape--d" /></div>
      <div class="welcome-grid" /><div class="welcome-glow" />
    </section>
  </main>
</template>

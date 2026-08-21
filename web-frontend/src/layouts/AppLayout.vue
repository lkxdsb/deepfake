<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'

const route = useRoute()
const system = useSystemStore()
const navOpen = ref(false)
const mainClass = computed(() => String(route.meta.mainClass || ''))
const navigation = [
  { label: '首页', meta: '平台总览、核心入口与流程指引', to: '/', wide: true },
  { label: '视频检测', meta: '上传视频并输出关键帧、热力图与判定结果', to: '/detect/video', wide: true },
  { label: '图片检测', meta: '面向单图伪造痕迹定位与置信度分析', to: '/detect/image' },
  { label: '音频检测', meta: '语音 deepfake 识别与概率输出', to: '/detect/audio' },
  { label: '历史中心', meta: '查看批次记录、结果汇总与统计趋势', to: '/history' },
  { label: 'AI 问答', meta: '解释检测结果并辅助答辩表达', to: '/chat' },
  { label: '科普频道', meta: '反诈知识、识别信号与场景案例', to: '/education' },
  { label: '闯关答题', meta: '互动题库训练与识别能力自测', to: '/quiz' },
]

function isActive(path: string) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}

watch(() => route.fullPath, () => (navOpen.value = false))
watch(navOpen, (open) => document.body.classList.toggle('nav-hover-open', open))
onMounted(() => system.refreshHealth())
</script>

<template>
  <div class="top-hover-zone" aria-hidden="true" />
  <nav id="top-hover-nav" class="top-hover-nav" aria-label="主导航" @mouseleave="navOpen = false">
    <div class="top-hover-nav__inner">
      <section class="top-hover-nav__hero">
        <p class="top-hover-nav__eyebrow">Deepfake Forensics System</p>
        <h2 class="top-hover-nav__title">灵眸鉴真</h2>
        <p class="top-hover-nav__intro">基于 CASE + Bi-ST 与 XLS-R-2B 的多模态深伪检测系统，支持图片、视频、音频统一检测与可解释证据输出。</p>
      </section>
      <div class="top-hover-nav__grid">
        <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" class="top-hover-nav__link" :class="{ 'top-hover-nav__link--wide': item.wide, 'is-active': isActive(item.to) }">
          <span class="top-hover-nav__label">{{ item.label }}</span><span class="top-hover-nav__meta">{{ item.meta }}</span>
        </RouterLink>
      </div>
    </div>
  </nav>
  <div class="bg-3d-scene" aria-hidden="true">
    <span class="bg-3d-shape bg-shape-prism-a" /><span class="bg-3d-shape bg-shape-prism-b" />
    <span class="bg-3d-shape bg-shape-cube-a" /><span class="bg-3d-shape bg-shape-diamond-a" />
    <span class="bg-3d-shape bg-shape-diamond-b" /><span class="bg-3d-shape bg-shape-frame-a" /><span class="bg-3d-shape bg-shape-ribbon-a" />
  </div>
  <div class="site-shell">
    <header class="site-header">
      <div class="site-header__inner">
        <RouterLink to="/" class="brand"><span class="brand-mark" aria-hidden="true"><img src="/static/images/logo.png" alt="" /></span><span class="brand-copy"><strong>灵眸鉴真</strong><span>Deepfake Forensics System</span></span></RouterLink>
        <p class="platform-intro">基于 CASE + Bi-ST 与 XLS-R-2B 的图像、视频、音频一体化深伪检测系统，支持统一检测、证据解析与结果导出。</p>
        <button class="top-nav-toggle" type="button" aria-controls="top-hover-nav" :aria-expanded="navOpen" @click="navOpen = !navOpen">菜单</button>
      </div>
    </header>
    <main class="site-main" :class="mainClass"><RouterView /></main>
    <footer class="site-footer"><div class="site-footer__inner"><p>&copy; 2026 灵眸鉴真项目组 版权所有</p></div></footer>
  </div>
</template>

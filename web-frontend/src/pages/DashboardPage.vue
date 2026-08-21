<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/services/api'
import type { HistorySummary } from '@/types/api'

const summary = ref<HistorySummary | null>(null)
const demoStatus = ref('支持 JPG / PNG / MP4 / WAV / MP3 / 历史记录与结果追踪')
const runningDemo = ref(false)
onMounted(async () => { try { summary.value = await api.summary() } catch { summary.value = null } })
async function runDemo() {
  runningDemo.value = true
  demoStatus.value = '示例任务需要算法服务与演示素材，正在检查...'
  try {
    const response = await fetch('/api/demo/run?mode=video', { method: 'POST' })
    const payload = await response.json()
    if (!response.ok || payload.code !== 0) throw new Error(payload.message || 'demo failed')
    window.location.href = `/results/${payload.data.task_id}`
  } catch (error) { demoStatus.value = `示例运行失败：${error instanceof Error ? error.message : '服务不可用'}` }
  finally { runningDemo.value = false }
}
</script>

<template>
  <section class="homev2-hero line-container">
    <div class="homev2-hero__copy">
      <div class="homev2-copy-main">
        <p class="homev2-eyebrow">专业 · 可解释 · 值得信任</p><h1>灵眸鉴真</h1>
        <p class="homev2-lede">基于 CASE + Bi-ST 与 XLS-R-2B 的图像、视频、音频一体化深伪检测系统，通过多模态协同分析输出风险评分、关键证据解释与检测报告，适用于内容安全治理、媒体真实性核验、远程身份核验等多个方向</p>
        <div class="homev2-actions"><RouterLink class="button button--primary" to="/detect/video">开始检测</RouterLink><button class="button button--secondary" type="button" :disabled="runningDemo" @click="runDemo">查看示例报告</button></div>
        <p class="homev2-support" :class="{ 'is-pending': runningDemo }">{{ demoStatus }}</p>
      </div>
      <aside class="homev2-copy-rail"><div class="homev2-kpi-grid">
        <article><span>支持模态</span><strong>3</strong><p>图像 / 视频 / 音频</p></article><article><span>平均耗时</span><strong>2.3s</strong><p>批次内自动检测</p></article><article><span>可解释项</span><strong>4+</strong><p>热力图与证据链</p></article><article><span>导出格式</span><strong>3</strong><p>PDF / JSON / CSV</p></article>
      </div><div class="homev2-mini-flow"><h4>检测流程</h4><ol><li>上传样本</li><li>自动分析</li><li>查看证据</li><li>导出报告</li></ol></div></aside>
    </div>
    <article class="homev2-result">
      <div class="homev2-result__head"><div><p>检测结果</p><strong>92.4%</strong><section class="homev2-evidence homev2-evidence--inline"><h3>主要证据</h3><ul><li>人脸边界异常</li><li>嘴型与音频不同步</li><li>音频轨迹异常</li><li>元数据缺失</li></ul></section></div><span class="homev2-risk">高风险</span></div>
      <div class="homev2-result__body"><section class="homev2-preview"><div class="homev2-preview__video"><img src="/static/images/hero-forensics.jpg" alt="检测预览" /><div class="homev2-preview__controls"><span>0:00 / 0:10</span></div></div><div class="homev2-preview__mini"><div class="homev2-mini-card"><span>人脸热力图（关键帧）</span><img src="/static/images/heatmap.webp" alt="热力图" /></div><div class="homev2-mini-card"><span>音频波形</span><div class="homev2-waveform" /></div></div></section></div>
      <div class="homev2-result__meta"><span><strong>文件名</strong> sample.mp4</span><span><strong>分辨率</strong> 1920 × 1080</span><span><strong>时长</strong> 00:10</span><span><strong>检测时间</strong> {{ summary?.latest_created_at || '暂无历史记录' }}</span></div>
    </article>
  </section>
  <section class="homev2-strip"><article><span class="homev2-strip__icon"><img src="/static/icons/tabler/photo-video.svg" alt="" /></span><div><h3>支持多模态检测</h3><p>图像、视频、音频协同分析</p></div></article><article><span class="homev2-strip__icon"><img src="/static/icons/tabler/zoom-check.svg" alt="" /></span><div><h3>结果可解释</h3><p>证据高亮与可视化输出</p></div></article><article><span class="homev2-strip__icon"><img src="/static/icons/tabler/history.svg" alt="" /></span><div><h3>历史记录</h3><p>追踪与复核管理</p></div></article><article><span class="homev2-strip__icon"><img src="/static/icons/tabler/file-export.svg" alt="" /></span><div><h3>报告导出</h3><p>PDF / JSON / CSV</p></div></article></section>
  <section class="section-block homev2-section"><div class="section-heading"><h2>核心功能入口</h2></div><div class="homev2-entry-grid">
    <article v-for="item in [{icon:'photo.svg',title:'图片检测',text:'分析人脸、纹理等，发现伪造痕迹。',to:'/detect/image'},{icon:'video.svg',title:'视频检测',text:'时序异常、帧级分析与一致性校验。',to:'/detect/video'},{icon:'wave-sine.svg',title:'音频检测',text:'检测合成语音与声纹篡改。',to:'/detect/audio'},{icon:'file-description.svg',title:'历史记录与报告',text:'查看历史批次与导出结果。',to:'/history'}]" :key="item.to" class="homev2-entry"><h3 class="homev2-title-row"><img :src="`/static/icons/tabler/${item.icon}`" alt="" /><span>{{ item.title }}</span></h3><p>{{ item.text }}</p><RouterLink :to="item.to">{{ item.to === '/history' ? '查看记录' : '立即检测' }}</RouterLink></article>
  </div></section>
  <section class="section-block homev2-section"><div class="section-heading"><h2>检测流程</h2></div><div class="homev2-flow"><article v-for="(step, index) in [['上传文件','选择图片、视频或音频文件','待上传'],['自动检测','多模态模型分析与风险评分','分析中'],['查看证据','查看可视化证据与详细解释','可查看'],['导出报告','下载 PDF / JSON / CSV','可下载']]" :key="String(step[0])" class="homev2-step"><div class="homev2-step__top"><span class="homev2-step__num">{{ index + 1 }}</span><span class="homev2-step__status">{{ step[2] }}</span></div><h3>{{ step[0] }}</h3><p>{{ step[1] }}</p></article></div></section>
  <section class="section-block homev2-section"><div class="section-heading"><h2>为什么值得信任</h2></div><div class="homev2-trust-grid"><article><h3 class="homev2-title-row"><img src="/static/icons/tabler/zoom-check.svg" alt="" /><span>可解释</span></h3><p>提供具体证据，不只是一个分数，让判断更清晰。</p></article><article><h3 class="homev2-title-row"><img src="/static/icons/tabler/chart-arcs-3.svg" alt="" /><span>风险分级</span></h3><p>低 / 中 / 高风险分级，便于决策与复核。</p></article><article><h3 class="homev2-title-row"><img src="/static/icons/tabler/shield-check.svg" alt="" /><span>可复核与导出</span></h3><p>保留完整记录，支持报告导出与安全审计。</p></article></div><figure class="homev2-trust-figure"><img src="/static/images/trust-method-compare.png" alt="Method comparison diagram" /><figcaption>CASE + temporal modeling + CLIP alignment provide stronger evidence than frame-only baselines.</figcaption></figure></section>
</template>

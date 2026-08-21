<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BarChart3, Clock3, FileArchive, FileSearch, Headphones, Image, Layers3, Play, ShieldCheck, UploadCloud, Video, Waves } from 'lucide-vue-next'
import { api, errorMessage } from '@/services/api'
import type { BatchResult, DetectionResult, MediaKind } from '@/types/api'

const route = useRoute()
const router = useRouter()
const input = ref<HTMLInputElement | null>(null)
const files = ref<File[]>([])
const batchName = ref('')
const dragging = ref(false)
const submitting = ref(false)
const status = ref('')
const kind = computed(() => route.params.kind as MediaKind)
const config = computed(() => ({
  image: { noun:'图片', title:'图像检测工作台', eyebrow:'Image Forensics Surface', intro:'上传单张或多张图片，系统将输出整体真伪结论、置信度与重点区域热力图，帮助您在演示与答辩场景中快速讲清“输入样本到证据解释”的完整流程。', formats:'jpg / jpeg / png', accept:'.jpg,.jpeg,.png', max:20, icon:Image, hint:'建议填写任务名，便于结果页和历史页区分不同批次。', placeholder:'例如：待检测图片样本' },
  video: { noun:'视频', title:'视频检测工作台', eyebrow:'Video Forensics Surface', intro:'上传单个或批量视频文件，系统将综合分析视频内容，输出整体真实性判断、关键帧证据、帧级风险曲线与热力图结果，便于在答辩或演示中完成从输入到证据解释的完整展示。', formats:'mp4 / avi / mov / mkv', accept:'.mp4,.avi,.mov,.mkv', max:500, icon:Video, hint:'视频分析相对耗时，建议优先上传时长较短、内容清晰的视频样本，以提升现场演示的流畅度。', placeholder:'例如：待检测视频样本' },
  audio: { noun:'音频', title:'音频检测工作台', eyebrow:'Audio Forensics Surface', intro:'上传单个或批量音频文件，系统将输出整体真伪判断、伪造概率、阈值与音频基础信息，帮助您快速识别语音克隆和合成音频风险。', formats:'wav / mp3 / flac', accept:'.wav,.mp3,.flac', max:100, icon:Waves, hint:'建议优先上传语音清晰、背景噪声较少的音频样本，以获得更稳定的检测结果。', placeholder:'例如：待检测音频样本' },
})[kind.value])

const prefix = computed(() => kind.value)
const totalSize = computed(() => files.value.reduce((sum, file) => sum + file.size, 0))
const summary = computed(() => files.value.length ? `已选择 ${files.value.length} 个文件 · ${formatSize(totalSize.value)}` : '尚未选择文件')

function formatSize(bytes:number) { const mb = bytes / 1024 / 1024; return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(1)} KB` }
function addFiles(list: FileList | File[]) {
  const incoming = Array.from(list)
  const allowed = config.value.accept.split(',')
  const existing = new Set(files.value.map(file => `${file.name}-${file.size}-${file.lastModified}`))
  for (const file of incoming) {
    if (files.value.length >= 20) { status.value = '单个批次最多提交 20 个文件。'; break }
    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!allowed.includes(ext)) { status.value = `${file.name} 的格式不受支持。`; continue }
    if (file.size > config.value.max * 1024 * 1024) { status.value = `${file.name} 超过 ${config.value.max} MB 限制。`; continue }
    const key = `${file.name}-${file.size}-${file.lastModified}`
    if (!existing.has(key)) { files.value.push(file); existing.add(key) }
  }
}
function drop(event: DragEvent) { dragging.value = false; if (event.dataTransfer?.files) addFiles(event.dataTransfer.files) }
async function submit() {
  if (!files.value.length || submitting.value) { status.value = `请先选择${config.value.noun}文件。`; return }
  submitting.value = true
  status.value = `检测中，共 ${files.value.length} 个${config.value.noun}，请稍候...`
  try {
    const result = await api.detect(kind.value, files.value, batchName.value) as DetectionResult | BatchResult
    const taskId = 'batch_task_id' in result ? result.batch_task_id : result.task_id
    await router.push(`/results/${taskId}`)
  } catch (error) { status.value = `检测失败：${errorMessage(error)}` }
  finally { submitting.value = false }
}
function reset() { files.value = []; batchName.value = ''; status.value = `待命中。上传${config.value.noun}后即可开始分析，请耐心等待结果生成。` }
watch(kind, () => { reset(); document.body.className = `theme-containers-b page-workbench page-workbench-${kind.value}` }, { immediate:true })
</script>

<template>
  <section :class="`${prefix}-workbench`">
    <section :class="`${prefix}-workbench__hero`">
      <div :class="`${prefix}-workbench__copy`"><div :class="`${prefix}-workbench__title-row`"><div :class="`${prefix}-workbench__badge`"><component :is="config.icon" /></div><div class="section-heading" :class="`${prefix}-workbench__heading`"><p class="eyebrow">{{ config.eyebrow }}</p><h1>{{ config.title }}</h1><p>{{ config.intro }}</p></div></div>
        <div v-if="kind === 'video'" class="quick-pills video-workbench__pills"><span><ShieldCheck />支持格式：{{ config.formats }}</span><span><UploadCloud />批量上传与任务命名</span><span><BarChart3 />可视化结果展示</span></div>
      </div>
      <aside v-if="kind !== 'video'" :class="`${prefix}-workbench__rail`"><div class="quick-pills" :class="[`${prefix}-workbench__pills`, `${prefix}-workbench__pills--stack`] "><span><ShieldCheck />支持格式：{{ config.formats }}</span><span><UploadCloud />批量上传</span><span><BarChart3 />可视化结果展示</span></div></aside>
      <div :class="`${prefix}-workbench__art`" aria-hidden="true"><template v-if="kind === 'image'"><div class="image-workbench__art-stack"><span class="image-workbench__sheet image-workbench__sheet--a"/><span class="image-workbench__sheet image-workbench__sheet--b"/><span class="image-workbench__sheet image-workbench__sheet--c"/></div><div class="image-workbench__magnifier"><span class="image-workbench__magnifier-ring"/><span class="image-workbench__magnifier-handle"/></div></template><template v-else-if="kind === 'video'"><span class="video-workbench__halo video-workbench__halo--a"/><span class="video-workbench__halo video-workbench__halo--b"/><span class="video-workbench__crystal video-workbench__crystal--a"/><span class="video-workbench__crystal video-workbench__crystal--b"/><span class="video-workbench__crystal video-workbench__crystal--c"/><span class="video-workbench__wave"/></template><template v-else><span class="audio-workbench__halo audio-workbench__halo--a"/><span class="audio-workbench__halo audio-workbench__halo--b"/><div class="audio-workbench__mic"><Waves /></div></template></div>
    </section>

    <section class="workbench-layout" :class="`${prefix}-workbench__layout`">
      <section class="workbench-panel workbench-panel--primary" :class="`${prefix}-upload-panel`"><div :class="`${prefix}-section-heading`"><span :class="`${prefix}-step`">1</span><div><h2>上传{{ config.noun }}</h2><p>{{ config.hint }}</p></div></div>
        <form class="forensics-form" @submit.prevent="submit"><div :class="`${prefix}-field-head`"><label class="field-label">任务名称 <span>选填</span></label><span :class="`${prefix}-field-counter`"><strong>{{ batchName.length }}</strong> / 50</span></div><input v-model="batchName" class="text-input" type="text" :placeholder="config.placeholder" maxlength="50" />
          <input ref="input" :class="`${prefix}-file-input`" type="file" :accept="config.accept" multiple @change="addFiles(($event.target as HTMLInputElement).files || [])" />
          <div :class="[`${prefix}-dropzone`, { 'is-dragover': dragging }]" tabindex="0" role="button" @click="input?.click()" @keydown.enter="input?.click()" @dragenter.prevent="dragging=true" @dragover.prevent="dragging=true" @dragleave.prevent="dragging=false" @drop.prevent="drop"><div :class="`${prefix}-dropzone__icon`"><UploadCloud /></div><strong>拖拽{{ config.noun }}到此处，或点击选择文件</strong><p>支持单个或批量上传，单个文件不超过 {{ config.max }}MB。</p><button class="button button--primary" :class="`${prefix}-dropzone__button`" type="button" @click.stop="input?.click()">选择{{ config.noun }}文件</button><div :class="`${prefix}-dropzone__meta`"><span>{{ summary }}</span><span>支持多文件批量检测</span></div></div>
          <ul v-if="files.length" :class="`${prefix}-file-list`"><li v-for="file in files.slice(0,5)" :key="`${file.name}-${file.size}`"><span>{{ file.name }}</span><small>{{ formatSize(file.size) }}</small></li><li v-if="files.length > 5"><span>其余 {{ files.length - 5 }} 个文件</span><small>已加入待检测队列</small></li></ul>
          <button class="button button--primary button--full" :class="`${prefix}-submit-button`" type="submit" :disabled="submitting"><Play />{{ submitting ? '正在分析' : `开始${config.noun}检测` }}</button><p class="inline-status inline-status--muted" :class="`${prefix}-status`">{{ status || `待命中。上传${config.noun}后即可开始分析，请耐心等待结果生成。` }}</p>
        </form>
      </section>

      <aside class="workbench-panel workbench-panel--secondary" :class="`${prefix}-preview-panel`"><div :class="`${prefix}-section-heading`"><span :class="`${prefix}-step`">2</span><div><h2>您将看到</h2><p>系统将输出整体判定结果，并通过关键证据帮助您理解分析依据。</p></div></div><div :class="`${prefix}-preview-stack`">
        <article :class="[`${prefix}-preview-card`, `${prefix}-preview-card--verdict`] "><div :class="[`${prefix}-preview-card__icon`, `${prefix}-preview-card__icon--blue`] "><ShieldCheck /></div><div :class="`${prefix}-preview-card__copy`"><h3>{{ kind === 'video' ? '整体真实性判断' : '检测结果' }}</h3><p>输出{{ config.noun }}真伪判断结果与置信度，快速了解风险等级。</p></div><div :class="`${prefix}-preview-meter`"><span>判断结果：<strong>伪造</strong></span><small>置信度：91.4%</small><div :class="`${prefix}-preview-meter__track`"><span /></div></div></article>
        <article :class="`${prefix}-preview-card`"><div :class="[`${prefix}-preview-card__icon`, `${prefix}-preview-card__icon--mint`] "><FileSearch /></div><div :class="`${prefix}-preview-card__copy`"><h3>{{ kind === 'image' ? '重点区域' : kind === 'video' ? '关键帧提取' : '分数说明' }}</h3><p>{{ kind === 'audio' ? '展示模型输出分数与阈值信息，帮助理解判别依据。' : '通过可解释证据直观定位值得复核的内容。' }}</p></div><div v-if="kind === 'image'" class="image-preview-heatmap"><img src="/static/images/detection3.png" alt="重点区域示意图" /></div><div v-else-if="kind === 'video'" class="video-keyframe-strip"><figure><img src="/static/images/detection_video1.jpg" alt="关键帧" /></figure><figure><img src="/static/images/detection_video2.jpg" alt="关键帧" /></figure><figure><img src="/static/images/detection_video3.jpg" alt="关键帧" /></figure></div><div v-else class="audio-stat-grid"><div class="audio-stat"><small>伪造概率</small><strong>0.897</strong></div><div class="audio-stat"><small>判定阈值</small><strong>0.500</strong></div><div class="audio-stat audio-stat--time"><small>时长</small><strong>00:00:32</strong></div></div></article>
        <article v-if="kind !== 'image'" :class="`${prefix}-preview-card`"><div :class="[`${prefix}-preview-card__icon`, `${prefix}-preview-card__icon--violet`] "><component :is="kind === 'video' ? BarChart3 : Headphones" /></div><div :class="`${prefix}-preview-card__copy`"><h3>{{ kind === 'video' ? '帧级概率曲线' : '音频试听' }}</h3><p>{{ kind === 'video' ? '展示风险随时间变化的趋势，快速定位异常区间。' : '结果页可直接播放音频，便于对照与核验。' }}</p></div><div v-if="kind === 'video'" class="video-preview-curve"><span /><span /><span /></div><div v-else class="audio-player-preview"><button type="button">▶</button><span class="audio-player-preview__wave"/><small class="audio-player-preview__time">00:00 / 00:32</small></div></article>
        <article :class="`${prefix}-preview-card`"><div :class="[`${prefix}-preview-card__icon`, `${prefix}-preview-card__icon--peach`] "><FileArchive /></div><div :class="`${prefix}-preview-card__copy`"><h3>历史记录</h3><p>检测后自动保存记录，方便后续查看历史结果与对比分析。</p></div><RouterLink class="button button--ghost button--small" :class="`${prefix}-history-link`" to="/history">查看历史记录</RouterLink></article>
      </div></aside>
    </section>
    <section :class="`${prefix}-capability-strip`"><article v-for="item in [{icon:ShieldCheck,title:'高精度模型',text:`融合多模态深度特征，提升${config.noun}检测准确性。`},{icon:Layers3,title:'可解释性强',text:'提供分数与可视化证据辅助理解。'},{icon:Clock3,title:'隐私安全',text:'所有数据仅用于检测分析。'},{icon:FileArchive,title:'结果导出',text:'支持检测报告导出，便于分享与存档。'}]" :key="item.title" :class="`${prefix}-capability`"><div :class="`${prefix}-capability__icon`"><component :is="item.icon" /></div><div><strong>{{ item.title }}</strong><p>{{ item.text }}</p></div></article></section>
  </section>
</template>

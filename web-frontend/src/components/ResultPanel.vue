<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, Clock3, FileScan, Gauge, Images, Layers3 } from 'lucide-vue-next'
import type { BatchResult, DetectionResult } from '@/types/api'
import VerdictBadge from './VerdictBadge.vue'
import RiskBar from './RiskBar.vue'

const props = defineProps<{ result: DetectionResult | BatchResult }>()

const isBatch = computed(() => 'items' in props.result)
const single = computed(() => (isBatch.value ? null : (props.result as DetectionResult)))
const batch = computed(() => (isBatch.value ? (props.result as BatchResult) : null))

function assetUrl(value: unknown) {
  return typeof value === 'string' ? value : ''
}
</script>

<template>
  <section class="result-panel">
    <div class="section-heading">
      <div>
        <span class="eyebrow">ANALYSIS RESULT</span>
        <h2>{{ isBatch ? '批量检测已完成' : '检测结果' }}</h2>
      </div>
      <RouterLink
        class="button button-secondary"
        :to="`/history/${batch?.batch_task_id ?? single?.batch_task_id ?? single?.task_id}`"
      >查看完整报告<ArrowRight :size="17" /></RouterLink>
    </div>

    <template v-if="single">
      <div class="result-summary">
        <div class="verdict-hero" :class="{ fake: single.label === 'fake' }">
          <span>模型判定</span>
          <strong>{{ single.label === 'fake' ? '疑似伪造' : '倾向真实' }}</strong>
          <VerdictBadge :label="single.label" :score="single.score" />
        </div>
        <div class="result-facts">
          <div><Gauge :size="19" /><span>风险分值</span><strong>{{ (single.score * 100).toFixed(2) }}%</strong></div>
          <div><Clock3 :size="19" /><span>推理耗时</span><strong>{{ (single.inference_time ?? 0).toFixed(2) }} 秒</strong></div>
          <div><FileScan :size="19" /><span>样本文件</span><strong>{{ single.file_name }}</strong></div>
          <div><Layers3 :size="19" /><span>检测模型</span><strong>{{ single.model_name ?? '未提供' }}</strong></div>
        </div>
      </div>

      <div v-if="single.heatmap_url || single.curve_url || single.preview_video_url || single.keyframes?.length" class="evidence-section">
        <div class="subsection-title"><Images :size="19" /><div><strong>模型证据</strong><span>用于辅助复核，不应单独作为最终定论</span></div></div>
        <div class="evidence-grid">
          <figure v-if="single.heatmap_url" class="evidence-media">
            <img :src="assetUrl(single.heatmap_url)" alt="模型关注区域热力图" />
            <figcaption>关注区域热力图</figcaption>
          </figure>
          <figure v-if="single.curve_url" class="evidence-media">
            <img :src="assetUrl(single.curve_url)" alt="视频风险变化曲线" />
            <figcaption>风险变化曲线</figcaption>
          </figure>
          <figure v-if="single.preview_video_url" class="evidence-media evidence-video">
            <video :src="assetUrl(single.preview_video_url)" controls preload="metadata" />
            <figcaption>标注预览</figcaption>
          </figure>
        </div>
        <div v-if="single.keyframes?.length" class="keyframe-strip">
          <figure v-for="(frame, index) in single.keyframes" :key="frame">
            <img :src="assetUrl(frame)" :alt="`可疑关键帧 ${index + 1}`" />
            <figcaption>关键帧 {{ index + 1 }}</figcaption>
          </figure>
        </div>
      </div>
    </template>

    <template v-else-if="batch">
      <div class="batch-result-head">
        <div><span>批次名称</span><strong>{{ batch.batch_name }}</strong></div>
        <div><span>完成样本</span><strong>{{ batch.batch_size }}</strong></div>
        <div><span>批次编号</span><strong>{{ batch.batch_task_id }}</strong></div>
      </div>
      <div class="batch-items">
        <div v-for="(item, index) in batch.items" :key="item.task_id" class="batch-item">
          <span class="row-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="file-cell"><strong>{{ item.file_name }}</strong><small>{{ item.task_id }}</small></div>
          <VerdictBadge :label="item.label" compact />
          <RiskBar :value="item.score" show-label />
        </div>
      </div>
    </template>
  </section>
</template>

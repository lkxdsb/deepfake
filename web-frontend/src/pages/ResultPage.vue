<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, errorMessage } from '@/services/api'
import type { HistoryDetail } from '@/types/api'

const route = useRoute()
const detail = ref<HistoryDetail | null>(null)
const loading = ref(true)
const error = ref('')
const index = ref(0)
const item = computed(() => detail.value?.items[index.value])
const prevention = computed(() => ({
  image:[['先查图片原始来源','对可疑图片先做以图搜图、发布时间比对和来源账号核验，不要只根据转发截图判断真伪。'],['放大看局部细节','重点查看文字边缘、手指数量、饰品结构、镜面反射和人物轮廓融合处。'],['关键信息回到官方渠道','涉及证件、公文、聊天记录、中奖通知等图片时，应回到官方渠道交叉确认。']],
  video:[['先做人证复核','遇到领导视频指令或亲友视频求助，不要只信画面，立即切到电话回拨或线下确认身份。'],['重点看动态破绽','留意口型同步、眨眼频率、发丝边缘、手部动作和光影衔接。'],['高风险操作延迟执行','涉及转账、授权、公开传播时，完成身份复核和原始来源确认后再处理。']],
  audio:[['敏感请求先挂断回拨','涉及转账、验证码、账号变更时，挂断后主动拨打本人或官方号码核实。'],['留意声音异常一致性','重点识别语速过稳、情绪起伏不足、停顿不自然、背景噪声突然切换。'],['建立口令式二次验证','提前约定只有本人知道的问题或口令，重要语音请求必须补做验证。']],
})[item.value?.result.file_type || 'image'])
onMounted(async () => { try { detail.value = await api.historyDetail(String(route.params.taskId)) } catch (cause) { error.value = errorMessage(cause) } finally { loading.value = false } })
</script>

<template>
  <section class="result-shell">
    <div class="result-command"><div class="result-command__copy"><p class="eyebrow">{{ (detail?.items.length || 0) > 1 ? 'Batch Result' : 'Detection Result' }}</p><h1>{{ detail?.batch.batch_name || '结果未找到' }}</h1><p v-if="detail">任务 ID：{{ detail.batch.task_id }} · 文件类型：{{ detail.batch.file_type }} · 创建时间：{{ detail.batch.created_at }}</p><p v-else-if="error">{{ error }}</p></div><div v-if="(detail?.items.length || 0) > 1" class="pager-toolbar pager-toolbar--results"><span class="meta-pill">{{ index + 1 }} / {{ detail?.items.length }}</span><button class="button button--ghost button--small" :disabled="index === 0" @click="index--">上一条</button><button class="button button--primary button--small" :disabled="index >= (detail?.items.length || 1) - 1" @click="index++">下一条</button></div></div>
    <p v-if="loading" class="inline-status inline-status--pending">正在加载检测结果...</p>
    <template v-else-if="detail && item">
      <div class="metric-band"><div class="metric-tile"><span>批次数量</span><strong>{{ detail.batch.item_count }}</strong></div><div class="metric-tile"><span>可疑样本</span><strong>{{ detail.batch.fake_count }}</strong></div><div class="metric-tile"><span>平均分</span><strong>{{ detail.batch.avg_score.toFixed(4) }}</strong></div><div class="metric-tile"><span>总耗时</span><strong>{{ detail.batch.total_inference_time.toFixed(4) }}s</strong></div></div>
      <section class="result-slide active"><div class="verdict-hero" :class="`verdict-hero--${item.result.label}`"><div class="verdict-hero__copy"><p class="eyebrow">Sample {{ index + 1 }}</p><h2>{{ item.record.file_name }}</h2><p class="verdict-hero__desc">{{ item.result.file_type === 'video' ? '视频样本已完成时序研判，结果页按“结论优先、证据次之”的方式组织展示。' : item.result.file_type === 'audio' ? '音频样本已完成阈值比较与概率分析，可直接试听并解释模型判断依据。' : '图像样本已完成空间分析，优先展示真假结论与热力图证据。' }}</p><div class="chip-row"><span class="verdict-badge" :class="`verdict-badge--${item.result.label}`">{{ item.result.label.toUpperCase() }}</span><span class="meta-pill">{{ item.result.file_type }}</span><span class="meta-pill">{{ item.result.model_name }}</span></div></div><div class="verdict-meter"><span>置信度</span><strong>{{ item.result.score.toFixed(4) }}</strong><small>推理耗时 {{ (item.result.inference_time || 0).toFixed(4) }}s</small></div></div>
        <div class="result-grid"><article class="surface-panel surface-panel--media"><div class="panel-heading"><h3>样本预览</h3><p>优先展示最适合答辩说明的原始样本内容。</p></div><video v-if="item.result.file_type === 'video' && item.result.preview_video_url" controls class="result-media result-media--video" :src="item.result.preview_video_url"/><audio v-else-if="item.result.file_type === 'audio' && item.result.preview_url" controls class="audio-player" :src="item.result.preview_url"/><img v-else-if="item.result.preview_url || item.result.heatmap_url" class="result-media" :src="item.result.preview_url || item.result.heatmap_url" alt="preview"/><p v-else class="inline-note">暂无预览内容。</p></article><article class="surface-panel"><div class="panel-heading"><h3>结果摘要</h3><p>汇总当前样本最关键的判定指标。</p></div><div class="detail-grid"><div>文件名</div><div>{{ item.result.file_name }}</div><div>文件类型</div><div>{{ item.result.file_type }}</div><div>判定结果</div><div>{{ item.result.label.toUpperCase() }}</div><div>置信度</div><div>{{ item.result.score.toFixed(4) }}</div><div>推理耗时</div><div>{{ (item.result.inference_time || 0).toFixed(4) }}s</div><div>模型版本</div><div>{{ item.result.model_name }}</div></div></article></div>
        <article class="surface-panel prevention-panel" :class="`prevention-panel--${item.result.file_type}`"><div class="panel-heading prevention-panel__heading"><div><p class="eyebrow">AI Safety Guidance</p><h3>AI 防范建议</h3></div><p>检测结论应与身份复核、来源核验和既有业务流程共同使用。</p></div><div class="prevention-grid"><section v-for="(tip, tipIndex) in prevention" :key="tip[0]" class="prevention-card"><span class="prevention-card__index">0{{ tipIndex + 1 }}</span><h4>{{ tip[0] }}</h4><p>{{ tip[1] }}</p></section></div></article>
        <div v-if="item.result.heatmap_url || item.result.curve_url" class="result-grid"><article v-if="item.result.heatmap_url" class="surface-panel"><div class="panel-heading"><h3>热力图证据</h3><p>展示模型在空间维度上的关注区域。</p></div><img class="result-media" :src="item.result.heatmap_url" alt="heatmap"/></article><article v-if="item.result.curve_url" class="surface-panel"><div class="panel-heading"><h3>时序曲线</h3><p>展示视频帧级风险概率变化。</p></div><img class="result-media" :src="item.result.curve_url" alt="curve"/></article></div>
        <article v-if="item.result.keyframes?.length" class="surface-panel"><div class="panel-heading"><h3>关键帧证据</h3><p>从关键帧切片中快速观察高风险片段。</p></div><div class="media-grid"><img v-for="url in item.result.keyframes" :key="url" class="result-media result-media--thumb" :src="url" alt="keyframe"/></div></article>
      </section>
    </template>
  </section>
</template>

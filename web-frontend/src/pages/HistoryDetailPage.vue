<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { EChartsCoreOption } from 'echarts/core'
import EChart from '@/components/EChart.vue'
import { api, errorMessage } from '@/services/api'
import type { HistoryAnalytics, HistoryDetail } from '@/types/api'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const detail = ref<HistoryDetail | null>(null)
const analytics = ref<HistoryAnalytics | null>(null)

const verdictOption = computed<EChartsCoreOption>(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie',
    radius: ['48%', '72%'],
    center: ['50%', '43%'],
    avoidLabelOverlap: true,
    label: { formatter: '{b}\n{d}%' },
    itemStyle: { borderColor: '#fff', borderWidth: 3 },
    color: ['#d94b58', '#119b7f'],
    data: analytics.value?.verdict_share.map((item) => ({ name: item.name, value: item.value })) ?? [],
  }],
}))

const histogramOption = computed<EChartsCoreOption>(() => ({
  grid: { left: 42, right: 18, top: 20, bottom: 42 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: analytics.value?.score_histogram.map((item) => item.label) ?? [],
    axisLabel: { interval: 1, rotate: 30 },
  },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{
    type: 'bar',
    data: analytics.value?.score_histogram.map((item) => item.count) ?? [],
    barMaxWidth: 34,
    itemStyle: { color: '#3a79c5', borderRadius: [4, 4, 0, 0] },
  }],
}))

const topRiskOption = computed<EChartsCoreOption>(() => {
  const samples = [...(analytics.value?.top_risk_samples ?? [])].reverse()
  return {
    grid: { left: 145, right: 48, top: 18, bottom: 28 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: unknown) => Number(value).toFixed(4),
    },
    xAxis: { type: 'value', min: 0, max: 1 },
    yAxis: {
      type: 'category',
      data: samples.map((item) => item.file_name),
      axisLabel: { width: 125, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: samples.map((item) => item.score),
      label: { show: true, position: 'right', formatter: ({ value }: { value: unknown }) => Number(value).toFixed(3) },
      itemStyle: { color: '#d94b58', borderRadius: [0, 4, 4, 0] },
    }],
  }
})

async function load(taskId: string) {
  loading.value = true
  error.value = ''
  detail.value = null
  analytics.value = null
  try {
    ;[detail.value, analytics.value] = await Promise.all([
      api.historyDetail(taskId),
      api.historyAnalytics(taskId),
    ])
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

watch(
  () => String(route.params.taskId ?? ''),
  (taskId) => load(taskId),
  { immediate: true },
)
</script>

<template>
  <section class="history-shell">
    <div class="result-command">
      <div class="result-command__copy">
        <p class="eyebrow">Batch Detail</p>
        <h1>{{ detail?.batch.batch_name || '历史详情' }}</h1>
        <p v-if="detail">
          任务 ID：{{ detail.batch.task_id }} · 文件类型：{{ detail.batch.file_type }} · 创建时间：{{ detail.batch.created_at }}
        </p>
        <p v-else-if="error">任务不存在或暂时无法读取。</p>
      </div>
      <RouterLink v-if="detail" class="button button--primary button--small" :to="`/results/${detail.batch.task_id}`">
        打开结果页
      </RouterLink>
    </div>

    <p v-if="loading" class="inline-status inline-status--pending">正在加载历史详情...</p>
    <article v-else-if="error" class="surface-panel">
      <p class="inline-status inline-status--error">{{ error }}</p>
      <button class="button button--secondary button--small" type="button" @click="load(String(route.params.taskId ?? ''))">
        重新加载
      </button>
    </article>

    <template v-else-if="detail && analytics">
      <div class="metric-band">
        <div class="metric-tile"><span>文件数</span><strong>{{ detail.batch.item_count }}</strong></div>
        <div class="metric-tile"><span>可疑数</span><strong>{{ detail.batch.fake_count }}</strong></div>
        <div class="metric-tile"><span>可疑率</span><strong>{{ (analytics.suspicious_rate * 100).toFixed(1) }}%</strong></div>
        <div class="metric-tile"><span>平均分</span><strong>{{ detail.batch.avg_score.toFixed(4) }}</strong></div>
      </div>

      <article class="surface-panel">
        <div class="panel-heading">
          <h2>批次摘要</h2>
          <p>当前批次的核心统计信息。</p>
        </div>
        <div class="detail-grid">
          <div>任务名</div><div>{{ detail.batch.batch_name }}</div>
          <div>文件类型</div><div>{{ detail.batch.file_type }}</div>
          <div>文件数</div><div>{{ detail.batch.item_count }}</div>
          <div>可疑数</div><div>{{ detail.batch.fake_count }}</div>
          <div>可疑率</div><div>{{ (analytics.suspicious_rate * 100).toFixed(1) }}%</div>
          <div>平均分</div><div>{{ detail.batch.avg_score.toFixed(4) }}</div>
          <div>总耗时</div><div>{{ detail.batch.total_inference_time.toFixed(4) }}s</div>
          <div>创建时间</div><div>{{ detail.batch.created_at }}</div>
        </div>
      </article>

      <div class="analytics-grid analytics-grid--history-detail">
        <article class="surface-panel surface-panel--analytics chart-card chart-card--wide">
          <div class="panel-heading">
            <h2>批次结论摘要</h2>
            <p>用一段简短说明把批次规模、风险水平和最高风险样本串起来，方便现场讲解。</p>
          </div>
          <div class="narrative-panel"><p class="narrative-panel__text">{{ analytics.summary_text }}</p></div>
        </article>

        <article class="surface-panel surface-panel--analytics chart-card">
          <div class="panel-heading"><h3>真假占比</h3><p>先回答这一批“整体偏真还是偏假”。</p></div>
          <EChart v-if="analytics.verdict_share.length" class="chart-shell" :option="verdictOption" />
          <p v-else class="inline-note">暂无真假占比数据。</p>
        </article>

        <article class="surface-panel surface-panel--analytics chart-card">
          <div class="panel-heading"><h3>风险分布直方图</h3><p>观察该批次样本是否集中在阈值附近，还是已经明显分层。</p></div>
          <EChart v-if="analytics.score_histogram.length" class="chart-shell" :option="histogramOption" />
          <p v-else class="inline-note">暂无风险分布数据。</p>
        </article>

        <article class="surface-panel surface-panel--analytics chart-card chart-card--wide">
          <div class="panel-heading"><h3>Top 高风险样本</h3><p>按风险分倒序展示，便于优先打开最值得讲解的样本。</p></div>
          <EChart v-if="analytics.top_risk_samples.length" class="chart-shell chart-shell--short" :option="topRiskOption" />
          <p v-else class="inline-note">暂无风险排序数据。</p>
        </article>
      </div>

      <article v-if="detail.items.length" class="surface-panel">
        <div class="panel-heading"><h2>批次明细</h2><p>逐条查看样本结论，并可跳转到对应结果页。</p></div>
        <div class="table-shell">
          <table class="table">
            <thead><tr><th>序号</th><th>文件名</th><th>结果</th><th>分数</th><th>耗时</th><th>详情</th></tr></thead>
            <tbody>
              <tr v-for="(item, index) in detail.items" :key="item.record.task_id">
                <td>{{ index + 1 }}</td>
                <td>{{ item.record.file_name }}</td>
                <td><span class="verdict-badge" :class="`verdict-badge--${item.record.result_label}`">{{ item.record.result_label.toUpperCase() }}</span></td>
                <td>{{ item.record.score.toFixed(4) }}</td>
                <td>{{ item.record.inference_time.toFixed(4) }}s</td>
                <td><RouterLink :to="`/results/${item.record.task_id}`">打开结果页</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </template>
  </section>
</template>

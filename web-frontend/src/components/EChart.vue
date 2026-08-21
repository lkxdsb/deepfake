<script setup lang="ts">
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { init, use, type ECharts, type EChartsCoreOption } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

use([BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ option: EChartsCoreOption }>()
const root = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null
let observer: ResizeObserver | null = null

function render() {
  if (!root.value) return
  if (!chart) chart = init(root.value, undefined, { renderer: 'canvas' })
  chart.setOption(props.option, true)
}

watch(() => props.option, () => nextTick(render), { deep: true })

onMounted(() => {
  render()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(root.value!)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>

<template><div ref="root" class="echart-root" /></template>

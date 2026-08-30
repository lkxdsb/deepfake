<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { api, errorMessage } from '@/services/api'
import type { ChatMessage, RagIndexStatus, RagSource, RetrievalMode } from '@/types/api'

interface UiChatMessage extends ChatMessage {
  sources?: RagSource[]
  retrievalMode?: RetrievalMode
  refused?: boolean
}

const prompts = [
  ['深伪和普通修图有何区别？', '深度伪造和普通修图有什么区别？'],
  ['视频检测为何不能只看单帧？', '为什么视频检测不能只看单帧画面？'],
  ['热力图、关键帧、曲线怎么读？', '热力图、关键帧和概率曲线怎么看？'],
  ['疑似 AI 换脸先看什么？', '遇到疑似AI换脸内容，应该先看什么？'],
]

const messages = ref<UiChatMessage[]>([])
const question = ref('')
const sending = ref(false)
const error = ref('')
const thread = ref<HTMLElement | null>(null)
const maxHistoryMessageChars = 1800
const expandedSourceMessages = ref<Set<number>>(new Set())
const indexStatus = ref<RagIndexStatus | null>(null)
const indexStatusError = ref('')
const indexUpdating = ref(false)
const selectedRetrievalMode = ref<RetrievalMode>('HYBRID')
const retrievalModeOptions: Array<{ value: RetrievalMode; label: string }> = [
  { value: 'VECTOR', label: '向量检索' },
  { value: 'HYBRID', label: '混合检索' },
  { value: 'HYBRID_RERANK', label: '混合 + 精排' },
]

marked.setOptions({ breaks: true, gfm: true })

function scroll() {
  nextTick(() => thread.value?.scrollTo({ top: thread.value.scrollHeight }))
}

function compactHistory(content: string) {
  if (content.length <= maxHistoryMessageChars) return content
  return `${content.slice(0, maxHistoryMessageChars - 1)}…`
}

function renderMarkdown(content: string) {
  return DOMPurify.sanitize(marked.parse(content || '', { async: false }), {
    ALLOWED_TAGS: ['a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'li', 'ol', 'p', 'pre', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul'],
    ALLOWED_ATTR: ['href', 'title'],
  })
}

function hasSources(message: UiChatMessage) {
  return Boolean(message.sources?.length)
}

function sourcesExpanded(index: number) {
  return expandedSourceMessages.value.has(index)
}

function toggleSources(index: number) {
  const next = new Set(expandedSourceMessages.value)
  if (next.has(index)) next.delete(index)
  else next.add(index)
  expandedSourceMessages.value = next
}

function formatIndexTime(value?: string) {
  if (!value) return '尚未构建'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

async function refreshIndexStatus() {
  try {
    indexStatus.value = await api.ragIndexStatus()
    indexStatusError.value = ''
  } catch (caught) {
    indexStatusError.value = errorMessage(caught)
  }
}

async function updateIndex(rebuild = false) {
  if (indexUpdating.value) return
  if (rebuild && !window.confirm('将清空并重新写入 Chroma 与 Lucene 索引，确定继续吗？')) return
  indexUpdating.value = true
  indexStatusError.value = ''
  try {
    await (rebuild ? api.ragIndexRebuild() : api.ragIndexUpdate())
    await refreshIndexStatus()
  } catch (caught) {
    indexStatusError.value = errorMessage(caught)
  } finally {
    indexUpdating.value = false
  }
}

onMounted(refreshIndexStatus)

async function submit(value?: string) {
  const text = (value ?? question.value).trim()
  if (!text || sending.value) return

  question.value = ''
  error.value = ''
  const history: ChatMessage[] = messages.value.slice(-6).map(({ role, content }) => ({ role, content: compactHistory(content) }))
  messages.value.push({ role: 'user', content: text })
  const answer: UiChatMessage = { role: 'assistant', content: '' }
  messages.value.push(answer)
  sending.value = true
  scroll()

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ question: text, history, retrievalMode: selectedRetrievalMode.value }),
    })
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.message || '问答服务暂不可用')

    const reader = response.body?.getReader()
    if (!reader) throw new Error('浏览器未收到流式响应')
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const event of events) applyEvent(event, answer)
    }
  } catch (caught) {
    messages.value.pop()
    error.value = caught instanceof Error ? caught.message : '问答失败'
  } finally {
    sending.value = false
    scroll()
  }
}

function applyEvent(event: string, answer: UiChatMessage) {
  const name = event.split('\n').find((line) => line.startsWith('event:'))?.slice(6).trim()
  const raw = event.split('\n').filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim()).join('\n')
  if (!raw) return
  const data = JSON.parse(raw)
  if (name === 'start') {
    answer.retrievalMode = data.retrievalMode
    answer.refused = Boolean(data.refused)
  } else if (name === 'delta') {
    answer.content += data.content || ''
    scroll()
  } else if (name === 'sources') {
    answer.sources = Array.isArray(data) ? data : []
  } else if (name === 'done') {
    answer.refused = Boolean(data.refused)
    answer.retrievalMode = data.retrievalMode || answer.retrievalMode
    if (!answer.content) answer.content = data.answer || ''
  } else if (name === 'error') {
    throw new Error(data.message || '问答流中断')
  }
}

function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <section class="chat-app">
    <aside class="chat-sidebar">
      <div class="chat-sidebar__brand">
        <p class="eyebrow">Deepfake RAG</p>
        <h1>深度伪造检测问答</h1>
        <p>基于项目资料检索生成回答，并展示可追溯来源。</p>
      </div>
      <RouterLink class="chat-sidebar__back" to="/">返回首页</RouterLink>
      <div class="chat-sidebar__scope">
        <strong>检测原理、平台使用、数字取证、合成内容识别</strong>
        <p>相关问题优先检索知识库并展示来源；其他日常问题也可正常交流，但不会附带项目资料引用。</p>
      </div>
      <div class="chat-sidebar__section">
        <span class="chat-sidebar__label">快捷问题</span>
        <div class="chat-sidebar__prompts">
          <button v-for="prompt in prompts" :key="prompt[0]" class="chat-sidebar__prompt" type="button" @click="submit(prompt[1])">{{ prompt[0] }}</button>
        </div>
      </div>
      <section class="rag-index-card" aria-label="知识库索引状态">
        <div class="rag-index-card__heading">
          <span>知识库索引</span>
          <button type="button" :disabled="indexUpdating" @click="refreshIndexStatus">刷新</button>
        </div>
        <template v-if="indexStatus">
          <p class="rag-index-card__state" :class="{ 'is-ready': indexStatus.initialized }">
            {{ indexStatus.initialized ? '已就绪' : '未构建' }} · {{ indexStatus.chunkCount }} Chunk
          </p>
          <p>{{ indexStatus.documentCount }} 份文档 / {{ indexStatus.sourceCount }} 个来源</p>
          <p>更新于 {{ formatIndexTime(indexStatus.updatedAt) }}</p>
        </template>
        <p v-else-if="indexStatusError" class="rag-index-card__error">{{ indexStatusError }}</p>
        <p v-else>正在读取状态…</p>
        <div class="rag-index-card__actions">
          <button type="button" :disabled="indexUpdating" @click="updateIndex()">{{ indexUpdating ? '更新中…' : '增量更新' }}</button>
          <button type="button" :disabled="indexUpdating" @click="updateIndex(true)">重新构建</button>
        </div>
      </section>
      <div class="chat-sidebar__foot"><span>Enter 发送</span><span>Shift + Enter 换行</span></div>
    </aside>

    <div class="chat-main" :class="{ 'is-conversation': messages.length }">
      <div ref="thread" class="chat-canvas" aria-live="polite">
        <section v-if="!messages.length" class="chat-empty">
          <p class="chat-empty__eyebrow">Grounded Answers</p>
          <h2>从项目知识库开始提问</h2>
          <p class="chat-empty__lede">日常问题可直接交流；项目相关问题会优先检索资料并展示来源。</p>
        </section>
        <article v-for="(message, index) in messages" :key="index" class="chat-message" :class="`chat-message--${message.role}`">
          <div class="chat-message__meta">
            {{ message.role === 'user' ? '你' : 'AI 助手' }}
            <span v-if="message.role === 'assistant' && message.content" class="chat-answer-kind" :class="hasSources(message) ? 'chat-answer-kind--grounded' : 'chat-answer-kind--general'">
              {{ hasSources(message) ? '知识库回答' : '普通回答' }}
            </span>
          </div>
          <div class="chat-message__body chat-rich-text">
            <p v-if="message.role === 'assistant' && message.content && !hasSources(message)" class="chat-general-notice">
              未命中知识库：以下为模型通用回答，不附项目资料引用。
            </p>
            <div v-if="message.content" v-html="renderMarkdown(message.content)" />
            <p v-if="!message.content && sending && message.role === 'assistant'" class="vue-loading">正在检索并生成回答...</p>
          </div>
          <section v-if="message.sources?.length" class="rag-sources" aria-label="知识库来源">
            <button class="rag-sources__toggle" type="button" :aria-expanded="sourcesExpanded(index)" @click="toggleSources(index)">
              <span>知识库来源 · {{ message.retrievalMode }} · {{ message.sources.length }} 条</span>
              <span>{{ sourcesExpanded(index) ? '收起' : '展开' }}</span>
            </button>
            <div v-if="sourcesExpanded(index)" class="rag-sources__list">
              <article v-for="source in message.sources" :key="source.sourceId" class="rag-source">
                <strong>[{{ source.sourceId }}] {{ source.title }}</strong>
                <span>{{ source.path }}<template v-if="source.section"> · {{ source.section }}</template></span>
                <p>{{ source.quote }}</p>
              </article>
            </div>
          </section>
        </article>
      </div>
      <div class="chat-dock">
        <p v-if="error" class="chat-status">{{ error }}</p>
        <form class="chat-composer" @submit.prevent="submit()">
          <label class="retrieval-mode" title="仅影响项目相关问题的检索方式">
            <span>检索</span>
            <select v-model="selectedRetrievalMode" :disabled="sending">
              <option v-for="option in retrievalModeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <textarea v-model="question" class="chat-composer__input" rows="1" maxlength="2000" placeholder="输入问题，项目相关内容将自动检索知识库" @keydown="keydown" />
          <button class="chat-composer__submit" type="submit" :disabled="sending">{{ sending ? '生成中' : '发送' }}</button>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.chat-answer-kind { display: inline-flex; margin-left: 8px; padding: 2px 7px; border-radius: 999px; font-size: 11px; font-weight: 700; line-height: 1.2; vertical-align: middle; }
.chat-answer-kind--grounded { color: #27634c; background: #e6f4ed; }
.chat-answer-kind--general { color: #5c6471; background: #edf0f4; }
.chat-general-notice { margin: 0 0 10px; padding: 7px 10px; border-left: 3px solid #91a7bf; color: #5c6f82; background: #f3f6f9; font-size: 12px; line-height: 1.45; }
.chat-rich-text :deep(p) { margin: 0 0 10px; }
.chat-rich-text :deep(p:last-child) { margin-bottom: 0; }
.chat-rich-text :deep(h1), .chat-rich-text :deep(h2), .chat-rich-text :deep(h3), .chat-rich-text :deep(h4) { margin: 16px 0 8px; color: #1f3046; line-height: 1.35; }
.chat-rich-text :deep(h1) { font-size: 22px; }
.chat-rich-text :deep(h2) { font-size: 19px; }
.chat-rich-text :deep(h3), .chat-rich-text :deep(h4) { font-size: 16px; }
.chat-rich-text :deep(ul), .chat-rich-text :deep(ol) { margin: 8px 0; padding-left: 22px; }
.chat-rich-text :deep(li) { margin: 4px 0; }
.chat-rich-text :deep(blockquote) { margin: 10px 0; padding: 8px 12px; border-left: 3px solid #9ab5d3; color: #50647b; background: #f5f8fc; }
.chat-rich-text :deep(code) { padding: 1px 4px; border-radius: 3px; background: #edf1f6; color: #334b6b; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em; }
.chat-rich-text :deep(pre) { overflow-x: auto; margin: 10px 0; padding: 12px; border-radius: 6px; background: #1f2a3a; color: #edf4ff; }
.chat-rich-text :deep(pre code) { padding: 0; background: transparent; color: inherit; }
.chat-rich-text :deep(table) { display: block; overflow-x: auto; max-width: 100%; margin: 10px 0; border-collapse: collapse; }
.chat-rich-text :deep(th), .chat-rich-text :deep(td) { padding: 7px 9px; border: 1px solid #d8e1ed; text-align: left; }
.chat-rich-text :deep(th) { background: #eff4fa; }
.chat-rich-text :deep(a) { color: #2865a7; text-decoration: underline; }
.rag-sources { display: grid; gap: 8px; margin-top: 12px; }
.rag-sources__toggle { display: flex; justify-content: space-between; width: fit-content; padding: 0; border: 0; color: #557168; background: transparent; font-size: 12px; font-weight: 700; cursor: pointer; text-align: left; }
.rag-sources__toggle span + span { margin-left: 8px; color: #2c6953; }
.rag-sources__list { display: grid; gap: 8px; }
.rag-source { padding: 10px 12px; border-left: 3px solid #8ab8a9; background: #f4f8f6; border-radius: 4px; }
.rag-source strong, .rag-source span { display: block; }
.rag-source strong { color: #294a3e; font-size: 13px; }
.rag-source span { margin-top: 3px; color: #6a7b74; font-size: 12px; }
.rag-source p { margin-top: 6px; color: #44514c; font-size: 13px; line-height: 1.55; }
.rag-index-card { display: grid; gap: 6px; margin: 18px 0 0; padding: 13px; border: 1px solid #c8ddef; border-radius: 10px; background: rgba(245, 250, 255, .74); color: #5f7188; font-size: 12px; line-height: 1.45; }
.rag-index-card p { margin: 0; }
.rag-index-card__heading { display: flex; align-items: center; justify-content: space-between; color: #35516f; font-weight: 700; }
.rag-index-card__heading button { padding: 0; border: 0; color: #356fa7; background: none; font: inherit; cursor: pointer; }
.rag-index-card__state { color: #9b6414; font-weight: 700; }
.rag-index-card__state.is-ready { color: #2b7658; }
.rag-index-card__error { color: #b24c50; }
.rag-index-card__actions { display: flex; gap: 7px; margin-top: 3px; }
.rag-index-card__actions button { flex: 1; padding: 6px 8px; border: 1px solid #a9c3dd; border-radius: 5px; color: #315d89; background: #fff; font: inherit; font-size: 12px; cursor: pointer; }
.rag-index-card button:disabled { opacity: .55; cursor: not-allowed; }
.retrieval-mode { display: inline-flex; align-items: center; gap: 5px; margin: 0 8px 0 0; color: #58708d; font-size: 12px; white-space: nowrap; }
.retrieval-mode select { max-width: 112px; padding: 5px 6px; border: 1px solid #b7cae0; border-radius: 5px; color: #315d89; background: #f8fbff; font: inherit; }
</style>

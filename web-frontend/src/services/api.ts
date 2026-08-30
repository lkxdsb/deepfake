import axios from 'axios'
import type {
  ApiEnvelope,
  BatchResult,
  ChatMessage,
  RagIndexBuildResult,
  RagIndexStatus,
  RagChatResponse,
  RetrievalMode,
  DetectionResult,
  HealthStatus,
  HistoryAnalytics,
  HistoryBatch,
  HistoryDetail,
  HistorySummary,
  MediaKind,
} from '@/types/api'

const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || error.message || '请求失败，请稍后重试'
    return Promise.reject(new Error(message))
  },
)

async function unwrap<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  const { data } = await request
  if (data.code !== 0) throw new Error(data.message || '接口返回异常')
  return data.data
}

export const api = {
  async health(): Promise<HealthStatus> {
    const { data } = await http.get<HealthStatus>('/health')
    return data
  },

  detect(kind: MediaKind, files: File[], batchName?: string, onProgress?: (value: number) => void) {
    const body = new FormData()
    const field = files.length === 1 ? 'file' : 'files'
    files.forEach((file) => body.append(field, file))
    if (batchName?.trim()) body.append('batch_name', batchName.trim())
    return unwrap<DetectionResult | BatchResult>(
      http.post(`/detect/${kind}`, body, {
        timeout: 20 * 60_000,
        onUploadProgress: (event) => {
          if (event.total && onProgress) onProgress(Math.round((event.loaded / event.total) * 100))
        },
      }),
    )
  },

  history: () => unwrap<HistoryBatch[]>(http.get('/history')),
  summary: () => unwrap<HistorySummary>(http.get('/history/summary')),
  historyDetail: (taskId: string) => unwrap<HistoryDetail>(http.get(`/history/${encodeURIComponent(taskId)}`)),
  historyAnalytics: (taskId: string) =>
    unwrap<HistoryAnalytics>(http.get(`/history/${encodeURIComponent(taskId)}/analytics`)),

  ask(question: string, history: ChatMessage[], retrievalMode?: RetrievalMode) {
    return unwrap<RagChatResponse>(http.post('/chat/ask', { question, history, retrievalMode }))
  },

  ragIndexStatus: () => unwrap<RagIndexStatus>(http.get('/rag/index/status')),
  ragIndexUpdate: () => unwrap<RagIndexBuildResult>(http.post('/rag/index/update')),
  ragIndexRebuild: () => unwrap<RagIndexBuildResult>(http.post('/rag/index/rebuild')),
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '发生未知错误'
}

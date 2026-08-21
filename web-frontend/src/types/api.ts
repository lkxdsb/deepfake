export type MediaKind = 'image' | 'video' | 'audio'
export type Verdict = 'fake' | 'real' | string

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export interface HealthStatus {
  status: 'ok' | 'unavailable' | string
  message?: string
  business_backend?: string
  model_loaded?: boolean
  audio_model_loaded?: boolean
  model_name?: string
  device?: string
}

export interface DetectionResult {
  task_id: string
  file_name: string
  file_type: MediaKind
  label: Verdict
  score: number
  inference_time?: number
  model_name?: string
  batch_task_id?: string
  batch_name?: string
  batch_size?: number
  preview_url?: string
  preview_video_url?: string
  heatmap_url?: string
  curve_url?: string
  keyframes?: string[]
  frame_results?: Array<Record<string, unknown>>
  duration_sec?: number
  fake_prob?: number
  real_prob?: number
  threshold?: number
  [key: string]: unknown
}

export interface BatchResult {
  batch_task_id: string
  batch_name: string
  batch_size: number
  file_type: MediaKind
  task_ids: string[]
  items: Array<Pick<DetectionResult, 'task_id' | 'file_name' | 'label' | 'score'>>
}

export interface HistoryBatch {
  task_id: string
  batch_name: string
  file_type: MediaKind
  item_count: number
  fake_count: number
  avg_score: number
  total_inference_time: number
  created_at: string
  suspicious_rate: number
  short_label?: string
}

export interface ModalitySummary {
  file_type: MediaKind
  batch_count: number
  item_count: number
  fake_count: number
  real_count: number
  suspicious_rate: number
  avg_inference_time: number
}

export interface HistorySummary {
  total_tasks: number
  total_samples: number
  total_fake_samples: number
  total_real_samples: number
  overall_suspicious_rate: number
  latest_created_at?: string
  recent_batches: HistoryBatch[]
  modalities: ModalitySummary[]
}

export interface HistoryRecord {
  task_id: string
  file_name: string
  file_type: MediaKind
  result_label: Verdict
  score: number
  preview_path?: string
  created_at: string
  model_version: string
  inference_time: number
  batch_index: number
}

export interface HistoryDetail {
  batch: HistoryBatch & { total_inference_time: number }
  items: Array<{ record: HistoryRecord; result: DetectionResult }>
}

export interface HistoryAnalytics {
  item_count: number
  fake_count: number
  real_count: number
  avg_score: number
  suspicious_rate: number
  verdict_share: Array<{ name: string; label: string; value: number }>
  score_histogram: Array<{ label: string; count: number; start: number; end: number }>
  top_risk_samples: Array<Pick<DetectionResult, 'task_id' | 'file_name' | 'label' | 'score'>>
  summary_text: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

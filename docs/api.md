# API 文档（MVP）

## 健康检查
- `GET /api/health`

## 图片检测
- `POST /api/detect/image`
- FormData: `file`

## 视频检测
- `POST /api/detect/video`
- FormData: `file`

## 音频检测
- `POST /api/detect/audio`
- FormData: `file`
- 支持格式：`wav/mp3/flac`

## 历史记录
- `GET /api/history`
- `GET /api/history/{task_id}`

## 示例演示
- `POST /api/demo/run?mode=video`
- `POST /api/demo/run?mode=image`

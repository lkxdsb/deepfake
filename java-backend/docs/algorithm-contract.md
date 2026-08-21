# Algorithm Service Contract

The algorithm service is internal. It must not store business history, create batch IDs, or expose
chat and page endpoints.

## Health

```http
GET /v1/health
```

Returns an object describing visual and audio model readiness. Java adds its own backend marker and
publishes the combined response through `GET /api/health`.

## Inference

```http
POST /v1/inference/image
POST /v1/inference/video
POST /v1/inference/audio
Content-Type: multipart/form-data
```

Fields:

- `file`: required media file;
- `task_id`: task ID allocated by Java.

Minimum successful response:

```json
{
  "label": "fake",
  "score": 0.86,
  "inference_time": 1.23,
  "model_name": "model.ckpt"
}
```

Optional fields are passed through unchanged, including:

- `preview_url`, `preview_video_url`, `preview_duration_sec`;
- `heatmap_url`, `curve_url`, `keyframes`;
- `frame_results`, `fps`, `total_frames`, `best_clip_index`;
- audio probabilities, threshold, duration, and decision rule.

Artifact URLs must point below the shared `OUTPUT_ROOT` and start with `/outputs/`. This keeps local
paths out of public responses and allows Java to serve all generated files.

## Error Handling

Use regular HTTP status codes. Java maps network failures to `503` and malformed successful
responses to `502`. Error bodies are not persisted as detection history.

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from src.utility.builtin import ODLightningCLI, ODTrainer

from algorithm_service.config import Settings
from algorithm_service.image_utils import load_image_rgb, rgb_to_chw_uint8
from algorithm_service.video_utils import (
    chw_rgb_to_bgr,
    read_video_frames,
    select_keyframe_indices,
    sliding_clip_indices,
)
from algorithm_service.visualization import (
    crop_image_to_bbox,
    detect_and_crop_primary_face,
    detect_primary_face_bbox,
    extract_spatial_heatmap,
    overlay_heatmap_full,
    save_curve,
    smooth_face_bboxes,
)


class InferenceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.precision = "16" if self.device.type == "cuda" else "32"
        self._load_lock = threading.Lock()
        self.model = None
        self.transform = None
        self.model_name = settings.model_ckpt_path.name
        self.loaded = False

    def _build_cli(self) -> ODLightningCLI:
        args = [
            "-c",
            str(self.settings.model_cfg_path),
            "--trainer.logger=null",
            "--trainer.devices=1",
            f"--trainer.precision={self.precision}",
            "--model.init_args.attn_record=true",
            '--model.init_args.store_attrs=["q","k"]',
        ]
        return ODLightningCLI(
            run=False,
            trainer_class=ODTrainer,
            save_config_callback=None,
            parser_kwargs={"parser_mode": "yaml"},
            auto_configure_optimizers=False,
            seed_everything_default=1019,
            args=args,
        )

    def _load_model(self) -> None:
        cli = self._build_cli()
        model = cli.model
        ckpt_path = str(self.settings.model_ckpt_path)
        load_overrides = {
            "attn_record": True,
            "store_attrs": ["q", "k"],
        }
        try:
            model = model.__class__.load_from_checkpoint(ckpt_path, **load_overrides)
        except Exception as ex:
            logging.warning("Checkpoint strict loading failed: %s", ex)
            model = model.__class__.load_from_checkpoint(ckpt_path, strict=False, **load_overrides)

        model.eval()
        model.to(self.device)

        self.model = model
        self.transform = model.transform
        self.loaded = True

    def warmup(self) -> None:
        self.ensure_model_loaded()

    def ensure_model_loaded(self) -> None:
        if self.loaded:
            return
        with self._load_lock:
            if self.loaded:
                return
            self._load_model()

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "model_loaded": bool(self.loaded),
            "device": str(self.device),
            "model_name": self.model_name,
        }

    def _detect_video_face_bboxes(
        self,
        frames: List[torch.Tensor],
    ) -> List[Optional[Tuple[int, int, int, int]]]:
        raw_bboxes: List[Optional[Tuple[int, int, int, int]]] = []
        fallback_bbox: Optional[Tuple[int, int, int, int]] = None
        image_shape: Optional[Tuple[int, int, int]] = None

        for frame in frames:
            frame_bgr = chw_rgb_to_bgr(frame)
            if image_shape is None:
                image_shape = frame_bgr.shape
            bbox = detect_primary_face_bbox(frame_bgr, fallback_bbox=fallback_bbox)
            raw_bboxes.append(bbox)
            if bbox is not None:
                fallback_bbox = bbox

        if image_shape is None:
            return raw_bboxes
        return smooth_face_bboxes(raw_bboxes, image_shape=image_shape)

    def _build_dense_frame_scores(
        self,
        total_frames: int,
        clip_offsets: List[int],
        probs: List[float],
    ) -> np.ndarray:
        frame_scores = np.zeros((max(total_frames, 1),), dtype=np.float32)
        if total_frames <= 0 or not probs:
            return frame_scores[:total_frames]

        safe_offsets = [
            max(0, min(int(offset), total_frames - 1))
            for offset in clip_offsets[: len(probs)]
        ]
        if not safe_offsets:
            frame_scores[:total_frames] = float(np.mean(probs))
            return frame_scores[:total_frames]

        frame_scores[: safe_offsets[0] + 1] = float(probs[0])
        for idx, start in enumerate(safe_offsets):
            end = safe_offsets[idx + 1] if idx + 1 < len(safe_offsets) else total_frames
            end = max(start + 1, min(end, total_frames))
            frame_scores[start:end] = float(probs[idx])
        return frame_scores[:total_frames]

    def _open_preview_writer(
        self,
        task_id: str,
        width: int,
        height: int,
        fps: float,
    ) -> Tuple[Optional[cv2.VideoWriter], Optional[Path]]:
        base_path = self.settings.outputs_previews_dir / f"{task_id}_boxed_preview_raw"
        candidates = [
            ("MJPG", ".avi"),
            ("XVID", ".avi"),
            ("mp4v", ".mp4"),
        ]

        for codec, suffix in candidates:
            out_path = base_path.with_suffix(suffix)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            writer = cv2.VideoWriter(
                str(out_path),
                cv2.VideoWriter_fourcc(*codec),
                fps,
                (width, height),
            )
            if writer.isOpened():
                return writer, out_path
            writer.release()
            out_path.unlink(missing_ok=True)

        return None, None

    def _transcode_preview_for_web(self, task_id: str, source_path: Path) -> Optional[Path]:
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            logging.warning("ffmpeg not found; skipping web preview video for task %s", task_id)
            return None

        final_path = self.settings.outputs_previews_dir / f"{task_id}_boxed_preview.mp4"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.unlink(missing_ok=True)

        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            str(source_path),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(final_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not final_path.exists() or final_path.stat().st_size == 0:
            stderr_tail = (result.stderr or "").strip().splitlines()[-5:]
            logging.warning(
                "ffmpeg preview transcode failed for task %s: %s",
                task_id,
                " | ".join(stderr_tail) if stderr_tail else f"returncode={result.returncode}",
            )
            final_path.unlink(missing_ok=True)
            return None

        source_path.unlink(missing_ok=True)
        return final_path

    def _render_boxed_video_preview(
        self,
        task_id: str,
        frames: List[torch.Tensor],
        face_bboxes: List[Optional[Tuple[int, int, int, int]]],
        fps: float,
        probs: List[float],
        clip_offsets: List[int],
        best_clip_index: int,
    ) -> Tuple[Optional[Path], Optional[float]]:
        total_frames = len(frames)
        if total_frames == 0:
            return None, None

        first_frame = chw_rgb_to_bgr(frames[0])
        height, width = first_frame.shape[:2]
        effective_fps = fps if fps > 0 else 25.0
        preview_frame_budget = max(1, int(round(self.settings.video_preview_seconds * effective_fps)))

        anchor_offset = 0
        if probs and 0 <= best_clip_index < len(clip_offsets):
            anchor_offset = int(clip_offsets[best_clip_index])

        center_frame = max(0, min(anchor_offset, total_frames - 1))
        if total_frames <= preview_frame_budget:
            start_frame = 0
            end_frame = total_frames
        else:
            half_window = preview_frame_budget // 2
            start_frame = max(0, center_frame - half_window)
            end_frame = start_frame + preview_frame_budget
            if end_frame > total_frames:
                end_frame = total_frames
                start_frame = max(0, end_frame - preview_frame_budget)

        writer, out_path = self._open_preview_writer(task_id, width, height, effective_fps)
        if writer is None or out_path is None:
            logging.warning("Unable to open preview writer for task %s", task_id)
            return None, None

        frame_scores = self._build_dense_frame_scores(total_frames, clip_offsets, probs)

        try:
            for frame_idx in range(start_frame, end_frame):
                frame_bgr = chw_rgb_to_bgr(frames[frame_idx]).copy()
                frame_score = float(frame_scores[frame_idx]) if frame_idx < len(frame_scores) else 0.0
                frame_label = "FAKE" if frame_score >= self.settings.score_threshold else "REAL"
                color = (0, 0, 255) if frame_label == "FAKE" else (0, 180, 0)

                banner_height = 64
                overlay = frame_bgr.copy()
                cv2.rectangle(overlay, (0, 0), (width, banner_height), (18, 22, 30), -1)
                frame_bgr = cv2.addWeighted(overlay, 0.5, frame_bgr, 0.5, 0)

                cv2.putText(
                    frame_bgr,
                    f"Boxed preview  p(fake)={frame_score:.3f}",
                    (16, 26),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    f"{frame_label}  frame {frame_idx + 1}/{total_frames}",
                    (16, 52),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    color,
                    2,
                    cv2.LINE_AA,
                )

                bbox = face_bboxes[frame_idx] if frame_idx < len(face_bboxes) else None
                if bbox is not None:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    x1 = max(0, min(x1, width - 1))
                    x2 = max(0, min(x2, width - 1))
                    y1 = max(0, min(y1, height - 1))
                    y2 = max(0, min(y2, height - 1))
                    if x2 > x1 and y2 > y1:
                        thickness = max(2, int(round(min(width, height) * 0.004)))
                        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, thickness)
                        label_y = max(y1 - 10, banner_height + 24)
                        cv2.putText(
                            frame_bgr,
                            frame_label,
                            (x1, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            color,
                            2,
                            cv2.LINE_AA,
                        )
                else:
                    cv2.putText(
                        frame_bgr,
                        "FACE NOT FOUND",
                        (16, min(height - 16, banner_height + 30)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 209, 102),
                        2,
                        cv2.LINE_AA,
                    )

                writer.write(frame_bgr)
        finally:
            writer.release()

        final_path = self._transcode_preview_for_web(task_id, out_path)
        if final_path is None:
            return None, None

        preview_duration = round((end_frame - start_frame) / effective_fps, 3)
        return final_path, preview_duration

    @torch.inference_mode()
    def predict_image(self, image_path: Path) -> Dict[str, Any]:
        self.ensure_model_loaded()

        image_rgb = load_image_rgb(image_path)
        face_rgb, face_bbox = detect_and_crop_primary_face(image_rgb)
        frame = rgb_to_chw_uint8(face_rgb)
        clip = torch.stack([self.transform(frame) for _ in range(self.settings.num_frames)])
        batch = clip.unsqueeze(0).to(self.device)

        t0 = time.perf_counter()
        outputs = self.model.evaluate(batch)
        elapsed = time.perf_counter() - t0

        probs = outputs["logits"].softmax(dim=-1)[:, 1].detach().cpu().tolist()
        score = float(probs[0])
        label = "fake" if score >= self.settings.score_threshold else "real"
        heatmap = extract_spatial_heatmap(outputs.get("layer_attrs"), batch_index=0)

        return {
            "label": label,
            "score": score,
            "inference_time": round(float(elapsed), 4),
            "model_name": self.model_name,
            "image_rgb": image_rgb,
            "heatmap": heatmap,
            "face_bbox": face_bbox,
        }

    @torch.inference_mode()
    def predict_video(self, video_path: Path, task_id: str) -> Dict[str, Any]:
        self.ensure_model_loaded()

        frames, fps = read_video_frames(video_path)
        total_frames = len(frames)

        indices = sliding_clip_indices(
            num_frames_total=total_frames,
            fps=fps,
            num_frames=self.settings.num_frames,
            stride=self.settings.video_stride,
        )

        max_idx = int(indices[-1].item())
        clip_count = max(1, total_frames - max_idx)
        face_bboxes = self._detect_video_face_bboxes(frames)
        transformed_cache: Dict[int, torch.Tensor] = {}

        probs: List[float] = []
        clip_heatmaps: List[Optional[np.ndarray]] = []
        clip_offsets: List[int] = []

        batch_size = max(1, int(os.getenv("VIDEO_BATCH_SIZE", "24")))
        clip_step = max(1, int(os.getenv("VIDEO_CLIP_STEP", "4")))

        t0 = time.perf_counter()
        i = 0
        while i < clip_count:
            window_end = min(clip_count, i + batch_size * clip_step)
            starts = list(range(i, window_end, clip_step))
            cur_batch = len(starts)
            if cur_batch == 0:
                break

            clips = []
            for start in starts:
                if clip_count == 1 and total_frames <= max_idx:
                    clip_indices = indices
                else:
                    clip_indices = indices + start

                clip_frames = []
                for idx in clip_indices:
                    frame_idx = int(idx.item())
                    cached = transformed_cache.get(frame_idx)
                    if cached is None:
                        frame_rgb = frames[frame_idx].permute(1, 2, 0).numpy()
                        cropped_rgb = crop_image_to_bbox(frame_rgb, face_bboxes[frame_idx])
                        cached = self.transform(rgb_to_chw_uint8(cropped_rgb))
                        transformed_cache[frame_idx] = cached
                    clip_frames.append(cached)

                clip = torch.stack(clip_frames)
                clips.append(clip)

            batch = torch.stack(clips).to(self.device)
            outputs = self.model.evaluate(batch)
            batch_probs = outputs["logits"].softmax(dim=-1)[:, 1].detach().cpu().tolist()

            layer_attrs = outputs.get("layer_attrs")
            for j, prob in enumerate(batch_probs):
                probs.append(float(prob))
                clip_offsets.append(starts[j])
                clip_heatmaps.append(extract_spatial_heatmap(layer_attrs, batch_index=j))

            i = window_end

        elapsed = time.perf_counter() - t0

        score = float(np.mean(probs)) if probs else 0.0
        label = "fake" if score >= self.settings.score_threshold else "real"

        frame_results: List[Dict[str, Any]] = []
        for idx, prob in enumerate(probs):
            start_offset = clip_offsets[idx] if idx < len(clip_offsets) else idx * clip_step
            frame_results.append(
                {
                    "clip_index": idx,
                    "start_offset": int(start_offset),
                    "score": round(float(prob), 6),
                    "label": "fake" if prob >= self.settings.score_threshold else "real",
                }
            )

        best_clip_index = int(np.argmax(probs)) if probs else 0
        keyframe_clip_ids = select_keyframe_indices(probs, self.settings.keyframe_count)
        keyframes_saved: List[Path] = []
        keyframe_path_by_clip: Dict[int, Path] = {}
        for rank, clip_id in enumerate(keyframe_clip_ids, start=1):
            start_offset = clip_offsets[clip_id] if clip_id < len(clip_offsets) else clip_id * clip_step
            if clip_count == 1 and total_frames <= max_idx:
                frame_idx = int(indices[-1].item())
            else:
                frame_idx = min(max_idx + start_offset, total_frames - 1)

            frame_bgr = chw_rgb_to_bgr(frames[frame_idx])
            prob = probs[clip_id]
            text = f"offset={start_offset} p(fake)={prob:.3f}"
            cv2.putText(frame_bgr, text, (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

            out_path = self.settings.outputs_frames_dir / f"{task_id}_keyframe_{rank}.jpg"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_path), frame_bgr)
            keyframes_saved.append(out_path)
            keyframe_path_by_clip[clip_id] = out_path

        curve_path = self.settings.outputs_reports_dir / f"{task_id}_curve.png"
        save_curve(probs, curve_path)

        preview_path = keyframe_path_by_clip.get(best_clip_index, keyframes_saved[0] if keyframes_saved else None)
        preview_video_path, preview_duration_sec = self._render_boxed_video_preview(
            task_id=task_id,
            frames=frames,
            face_bboxes=face_bboxes,
            fps=fps,
            probs=probs,
            clip_offsets=clip_offsets,
            best_clip_index=best_clip_index,
        )
        best_attention_heatmap: Optional[np.ndarray] = None
        best_attention_bbox: Optional[Tuple[int, int, int, int]] = None
        best_attention_frame_bgr: Optional[np.ndarray] = None
        if 0 <= best_clip_index < len(clip_heatmaps):
            best_attention_heatmap = clip_heatmaps[best_clip_index]
            best_start_offset = clip_offsets[best_clip_index] if best_clip_index < len(clip_offsets) else best_clip_index * clip_step
            if clip_count == 1 and total_frames <= max_idx:
                best_frame_idx = int(indices[-1].item())
            else:
                best_frame_idx = min(max_idx + best_start_offset, total_frames - 1)
            best_attention_bbox = face_bboxes[best_frame_idx]
            best_attention_frame_bgr = chw_rgb_to_bgr(frames[best_frame_idx])

        return {
            "label": label,
            "score": round(score, 6),
            "inference_time": round(float(elapsed), 4),
            "model_name": self.model_name,
            "frame_results": frame_results,
            "keyframe_paths": keyframes_saved,
            "curve_path": curve_path,
            "preview_path": preview_path,
            "preview_video_path": preview_video_path,
            "preview_duration_sec": preview_duration_sec,
            "fps": fps,
            "total_frames": total_frames,
            "attention_heatmap": best_attention_heatmap,
            "attention_bbox": best_attention_bbox,
            "attention_frame_bgr": best_attention_frame_bgr,
            "best_clip_index": best_clip_index,
            "clip_step": clip_step,
            "batch_size": batch_size,
        }

    def render_image_heatmap(self, image_rgb: np.ndarray, heatmap: np.ndarray) -> np.ndarray:
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        return overlay_heatmap_full(image_bgr, heatmap)


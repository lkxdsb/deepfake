import math
from pathlib import Path
from typing import List, Tuple

import cv2
import torch


def read_video_frames(video_path: Path) -> Tuple[List[torch.Tensor], float]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Unable to open video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0

    frames: List[torch.Tensor] = []
    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frames.append(torch.from_numpy(frame_rgb).permute(2, 0, 1))

    cap.release()

    if not frames:
        raise ValueError("No frames decoded from video")

    return frames, float(fps)


def sliding_clip_indices(num_frames_total: int, fps: float, num_frames: int, stride: float) -> torch.Tensor:
    base = torch.tensor([int(math.floor(i * stride * fps)) for i in range(num_frames)], dtype=torch.long)
    max_idx = int(base[-1].item())
    if num_frames_total > max_idx:
        return base

    if num_frames_total == 1:
        return torch.zeros((num_frames,), dtype=torch.long)

    lin = torch.linspace(0, num_frames_total - 1, steps=num_frames)
    return lin.round().long()


def select_keyframe_indices(probs: List[float], k: int) -> List[int]:
    if not probs:
        return []
    ranked = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
    uniq = []
    for idx in ranked:
        if idx not in uniq:
            uniq.append(idx)
        if len(uniq) >= k:
            break
    return sorted(uniq)


def chw_rgb_to_bgr(frame: torch.Tensor):
    rgb = frame.permute(1, 2, 0).numpy()
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

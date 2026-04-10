from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


def extract_spatial_heatmap(
    layer_attrs: Optional[List[Dict[str, Any]]],
    batch_index: int = 0,
    last_n_layers: int = 4,
    time_index: int = -1,
) -> Optional[np.ndarray]:
    if not layer_attrs:
        return None

    maps: List[np.ndarray] = []
    target_layers = layer_attrs[-max(last_n_layers, 1) :]

    for attrs in target_layers:
        if not isinstance(attrs, dict):
            continue
        if "q" not in attrs or "k" not in attrs:
            continue

        q = attrs["q"]
        k = attrs["k"]

        if q is None or k is None:
            continue
        if q.ndim != 5 or k.ndim != 5:
            continue

        cls_q = q[:, :, 0, :, :]
        patch_k = k[:, :, 1:, :, :]

        cls_q = cls_q / (cls_q.norm(dim=-1, keepdim=True) + 1e-6)
        patch_k = patch_k / (patch_k.norm(dim=-1, keepdim=True) + 1e-6)

        score = torch.einsum("bthd,btphd->btph", cls_q, patch_k).mean(dim=-1)

        if batch_index < 0 or batch_index >= score.shape[0]:
            continue

        t_idx = time_index if time_index >= 0 else score.shape[1] + time_index
        t_idx = max(0, min(score.shape[1] - 1, t_idx))

        score_1d = score[batch_index, t_idx, :].detach().cpu().numpy()

        patch_num = score_1d.shape[-1]
        patch_grid = int(round(np.sqrt(patch_num)))
        if patch_grid * patch_grid != patch_num:
            continue

        map_2d = score_1d.reshape(patch_grid, patch_grid)
        map_2d = (map_2d - map_2d.min()) / (map_2d.max() - map_2d.min() + 1e-6)
        maps.append(map_2d)

    if not maps:
        return None

    heatmap = np.stack(maps, axis=0).mean(axis=0)
    return np.clip(heatmap, 0.0, 1.0)


def render_heatmap_strip(heatmap: np.ndarray, repeat: int = 5, gap: int = 6) -> np.ndarray:
    hm_u8 = (np.clip(heatmap, 0.0, 1.0) * 255).astype(np.uint8)
    hm_color = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)

    if repeat <= 1:
        return hm_color

    h, w = hm_color.shape[:2]
    strip_w = repeat * w + (repeat - 1) * gap
    strip = np.zeros((h, strip_w, 3), dtype=np.uint8)

    for i in range(repeat):
        x0 = i * (w + gap)
        strip[:, x0 : x0 + w] = hm_color

    return strip


def detect_primary_face_bbox(image_bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        return None

    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(36, 36),
    )
    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda item: int(item[2]) * int(item[3]))
    pad_x = int(w * 0.18)
    pad_y_top = int(h * 0.22)
    pad_y_bottom = int(h * 0.30)

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y_top)
    x2 = min(image_bgr.shape[1], x + w + pad_x)
    y2 = min(image_bgr.shape[0], y + h + pad_y_bottom)
    return x1, y1, x2, y2


def overlay_heatmap_full(image_bgr: np.ndarray, heatmap: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    hm = cv2.resize(heatmap, (w, h), interpolation=cv2.INTER_CUBIC)
    hm_u8 = (np.clip(hm, 0.0, 1.0) * 255).astype(np.uint8)
    hm_color = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)
    return cv2.addWeighted(image_bgr, 1.0 - alpha, hm_color, alpha, 0.0)


def overlay_heatmap_on_bbox(
    image_bgr: np.ndarray,
    heatmap: np.ndarray,
    bbox: Optional[Tuple[int, int, int, int]],
    alpha: float = 0.58,
) -> np.ndarray:
    if bbox is None:
        return overlay_heatmap_full(image_bgr, heatmap, alpha=alpha)

    x1, y1, x2, y2 = bbox
    if x2 <= x1 or y2 <= y1:
        return overlay_heatmap_full(image_bgr, heatmap, alpha=alpha)

    out = image_bgr.copy()
    hm = cv2.resize(heatmap, (x2 - x1, y2 - y1), interpolation=cv2.INTER_CUBIC)
    hm_u8 = (np.clip(hm, 0.0, 1.0) * 255).astype(np.uint8)
    hm_color = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)
    roi = out[y1:y2, x1:x2]
    out[y1:y2, x1:x2] = cv2.addWeighted(roi, 1.0 - alpha, hm_color, alpha, 0.0)
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 210, 255), 2)
    return out


def build_explainability_panel(
    image_bgr: np.ndarray,
    heatmap: np.ndarray,
    repeat: int = 5,
    gap: int = 10,
) -> np.ndarray:
    bbox = detect_primary_face_bbox(image_bgr)
    overlay = overlay_heatmap_on_bbox(image_bgr, heatmap, bbox=bbox)
    strip = render_heatmap_strip(heatmap, repeat=repeat, gap=6)

    target_h = max(image_bgr.shape[0], overlay.shape[0])
    target_w = max(image_bgr.shape[1], overlay.shape[1])
    left = cv2.resize(image_bgr, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    right = cv2.resize(overlay, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

    top = np.full((target_h, target_w * 2 + gap, 3), 255, dtype=np.uint8)
    top[:, :target_w] = left
    top[:, target_w + gap :] = right

    cv2.putText(top, "Preview", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (32, 32, 32), 2)
    cv2.putText(top, "Face-Focused Attention", (target_w + gap + 12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (32, 32, 32), 2)

    strip_w = top.shape[1]
    strip_h = max(120, int(strip.shape[0] * (strip_w / max(strip.shape[1], 1))))
    strip_resized = cv2.resize(strip, (strip_w, strip_h), interpolation=cv2.INTER_CUBIC)

    title_h = 42
    bottom = np.full((strip_h + title_h, strip_w, 3), 255, dtype=np.uint8)
    cv2.putText(bottom, "Patch Attention Strip", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (32, 32, 32), 2)
    bottom[title_h:, :] = strip_resized

    panel = np.full((top.shape[0] + gap + bottom.shape[0], strip_w, 3), 248, dtype=np.uint8)
    panel[: top.shape[0], :] = top
    panel[top.shape[0] + gap :, :] = bottom
    return panel


def save_curve(probabilities: List[float], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if len(probabilities) == 0:
        blank = np.full((400, 900, 3), 255, dtype=np.uint8)
        cv2.putText(blank, "No probabilities", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (30, 30, 30), 2)
        cv2.imwrite(str(out_path), blank)
        return

    if plt is not None:
        plt.figure(figsize=(10, 3))
        x = list(range(len(probabilities)))
        plt.plot(x, probabilities, color="#d62728", linewidth=2)
        plt.ylim(0.0, 1.0)
        plt.title("Frame-level Fake Probability")
        plt.xlabel("Clip Index")
        plt.ylabel("P(fake)")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(str(out_path), dpi=150)
        plt.close()
        return

    canvas = np.full((400, 900, 3), 255, dtype=np.uint8)
    cv2.rectangle(canvas, (50, 30), (850, 350), (80, 80, 80), 1)
    pts = []
    n = len(probabilities)
    for i, p in enumerate(probabilities):
        x = int(50 + (800 * (i / max(1, n - 1))))
        y = int(350 - (320 * float(p)))
        pts.append([x, y])
    if len(pts) >= 2:
        cv2.polylines(canvas, [np.array(pts, dtype=np.int32)], isClosed=False, color=(0, 0, 255), thickness=2)
    cv2.putText(canvas, "Frame-level Fake Probability", (50, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1)
    cv2.imwrite(str(out_path), canvas)

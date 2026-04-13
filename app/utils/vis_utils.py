from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

try:
    import face_alignment
except Exception:
    face_alignment = None


@lru_cache(maxsize=1)
def _load_face_detector() -> Optional[cv2.CascadeClassifier]:
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        return None
    return detector


@lru_cache(maxsize=1)
def _load_landmark_detector() -> Any:
    if face_alignment is None:
        return None
    try:
        return face_alignment.FaceAlignment(
            face_alignment.LandmarksType.TWO_D,
            face_detector="sfd",
            flip_input=False,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
    except Exception:
        return None


def _normalize_heatmap_map(heatmap: np.ndarray) -> np.ndarray:
    heatmap = np.asarray(heatmap, dtype=np.float32)
    min_val = float(heatmap.min())
    max_val = float(heatmap.max())
    if max_val - min_val <= 1e-6:
        return np.zeros_like(heatmap, dtype=np.float32)
    return np.clip((heatmap - min_val) / (max_val - min_val + 1e-6), 0.0, 1.0)


def _sparsify_heatmap(heatmap: np.ndarray, percentile: float = 72.0, gamma: float = 0.85) -> np.ndarray:
    heatmap = _normalize_heatmap_map(heatmap)
    threshold = float(np.percentile(heatmap, percentile))
    heatmap = np.clip(heatmap - threshold, 0.0, None)
    heatmap = _normalize_heatmap_map(heatmap)
    return np.power(heatmap, gamma).astype(np.float32)


def _infer_face_part_names(part_count: int) -> Tuple[str, ...]:
    if part_count == 4:
        return ("lips", "skin", "eyes", "nose")
    if part_count == 3:
        return ("lips", "eyes", "nose")
    if part_count == 2:
        return ("eyes", "nose")
    return tuple(f"part_{idx}" for idx in range(part_count))


def _build_face_component_priors(grid_size: int) -> Dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:grid_size, 0:grid_size].astype(np.float32)
    yy = yy / max(grid_size - 1, 1)
    xx = xx / max(grid_size - 1, 1)

    def gaussian(cx: float, cy: float, sx: float, sy: float) -> np.ndarray:
        return np.exp(-(((xx - cx) ** 2) / (2.0 * sx * sx) + ((yy - cy) ** 2) / (2.0 * sy * sy)))

    left_eye = gaussian(0.33, 0.36, 0.10, 0.08)
    right_eye = gaussian(0.67, 0.36, 0.10, 0.08)
    nose = gaussian(0.50, 0.55, 0.10, 0.14)
    mouth = gaussian(0.50, 0.76, 0.16, 0.10)

    return {
        "eyes": np.maximum(left_eye, right_eye).astype(np.float32),
        "nose": nose.astype(np.float32),
        "mouth": mouth.astype(np.float32),
    }


def _extract_landmarks_in_bbox(
    image_bgr: np.ndarray,
    bbox: Optional[Tuple[int, int, int, int]],
) -> Optional[np.ndarray]:
    if bbox is None:
        return None

    detector = _load_landmark_detector()
    if detector is None:
        return None

    x1, y1, x2, y2 = bbox
    if x2 <= x1 or y2 <= y1:
        return None

    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    try:
        if hasattr(detector, "get_landmarks_from_image"):
            preds = detector.get_landmarks_from_image(crop_rgb)
        else:
            preds = detector.get_landmarks(crop_rgb)
    except Exception:
        return None

    if preds is None or len(preds) == 0:
        return None

    landmarks = np.asarray(preds[0], dtype=np.float32)
    if landmarks.shape[0] < 68:
        return None
    landmarks[:, 0] += float(x1)
    landmarks[:, 1] += float(y1)
    return landmarks


def _polygon_mask(shape: Tuple[int, int], points: np.ndarray, blur: int = 9) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    if points.shape[0] < 3:
        return mask.astype(np.float32)

    hull = cv2.convexHull(points.astype(np.int32))
    cv2.fillConvexPoly(mask, hull, 255)

    if blur > 1:
        blur = blur + 1 if blur % 2 == 0 else blur
        mask = cv2.GaussianBlur(mask, (blur, blur), 0)
    return mask.astype(np.float32) / 255.0


def _landmark_component_masks(
    landmarks: np.ndarray,
    bbox: Tuple[int, int, int, int],
) -> Dict[str, np.ndarray]:
    x1, y1, x2, y2 = bbox
    roi_h = max(1, y2 - y1)
    roi_w = max(1, x2 - x1)

    pts = landmarks.copy()
    pts[:, 0] -= float(x1)
    pts[:, 1] -= float(y1)

    left_eye = _polygon_mask((roi_h, roi_w), pts[36:42], blur=11)
    right_eye = _polygon_mask((roi_h, roi_w), pts[42:48], blur=11)
    nose = _polygon_mask((roi_h, roi_w), pts[27:36], blur=15)
    mouth = _polygon_mask((roi_h, roi_w), pts[48:60], blur=15)

    eyes = np.maximum(left_eye, right_eye)
    return {
        "eyes": eyes.astype(np.float32),
        "nose": nose.astype(np.float32),
        "mouth": mouth.astype(np.float32),
    }


def _distance_weight(mask: np.ndarray) -> np.ndarray:
    mask_u8 = (np.clip(mask, 0.0, 1.0) * 255).astype(np.uint8)
    if mask_u8.max() == 0:
        return mask.astype(np.float32)
    dist = cv2.distanceTransform(mask_u8, cv2.DIST_L2, 3)
    return _normalize_heatmap_map(dist)


def _ellipse_mask(
    shape: Tuple[int, int],
    center: Tuple[int, int],
    axes: Tuple[int, int],
    angle: float = 0.0,
    blur: int = 11,
) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1)
    if blur > 1:
        blur = blur + 1 if blur % 2 == 0 else blur
        mask = cv2.GaussianBlur(mask, (blur, blur), 0)
    return mask.astype(np.float32) / 255.0


def _find_window_peak(
    heatmap: np.ndarray,
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
) -> Tuple[int, int]:
    h, w = heatmap.shape[:2]
    x1 = max(0, min(w - 1, int(round(x_range[0] * (w - 1)))))
    x2 = max(x1 + 1, min(w, int(round(x_range[1] * (w - 1))) + 1))
    y1 = max(0, min(h - 1, int(round(y_range[0] * (h - 1)))))
    y2 = max(y1 + 1, min(h, int(round(y_range[1] * (h - 1))) + 1))
    window = heatmap[y1:y2, x1:x2]
    if window.size == 0:
        return w // 2, h // 2
    peak_idx = int(window.argmax())
    peak_y, peak_x = np.unravel_index(peak_idx, window.shape)
    return x1 + int(peak_x), y1 + int(peak_y)


def _heuristic_component_masks(heatmap: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict[str, np.ndarray]:
    x1, y1, x2, y2 = bbox
    roi_h = max(1, y2 - y1)
    roi_w = max(1, x2 - x1)
    coarse = cv2.resize(heatmap, (roi_w, roi_h), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    coarse = _normalize_heatmap_map(coarse)

    left_eye_center = _find_window_peak(coarse, (0.18, 0.46), (0.18, 0.46))
    right_eye_center = _find_window_peak(coarse, (0.54, 0.82), (0.18, 0.46))
    nose_center = _find_window_peak(coarse, (0.36, 0.64), (0.34, 0.70))
    mouth_center = _find_window_peak(coarse, (0.28, 0.72), (0.60, 0.90))

    left_eye = _ellipse_mask(
        (roi_h, roi_w),
        left_eye_center,
        (max(6, int(roi_w * 0.08)), max(4, int(roi_h * 0.045))),
        blur=13,
    )
    right_eye = _ellipse_mask(
        (roi_h, roi_w),
        right_eye_center,
        (max(6, int(roi_w * 0.08)), max(4, int(roi_h * 0.045))),
        blur=13,
    )
    nose = _ellipse_mask(
        (roi_h, roi_w),
        nose_center,
        (max(6, int(roi_w * 0.055)), max(9, int(roi_h * 0.11))),
        blur=17,
    )
    mouth = _ellipse_mask(
        (roi_h, roi_w),
        mouth_center,
        (max(10, int(roi_w * 0.13)), max(5, int(roi_h * 0.055))),
        blur=17,
    )

    return {
        "eyes": np.maximum(left_eye, right_eye).astype(np.float32),
        "nose": nose.astype(np.float32),
        "mouth": mouth.astype(np.float32),
    }


def _refine_heatmap_with_landmarks(
    image_bgr: np.ndarray,
    heatmap: np.ndarray,
    bbox: Optional[Tuple[int, int, int, int]],
) -> np.ndarray:
    if bbox is None:
        return heatmap

    landmarks = _extract_landmarks_in_bbox(image_bgr, bbox)

    x1, y1, x2, y2 = bbox
    roi_h = max(1, y2 - y1)
    roi_w = max(1, x2 - x1)

    coarse = cv2.resize(heatmap, (roi_w, roi_h), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    coarse = _normalize_heatmap_map(coarse)
    masks = (
        _landmark_component_masks(landmarks, bbox)
        if landmarks is not None else
        _heuristic_component_masks(heatmap, bbox)
    )

    refined = np.zeros_like(coarse, dtype=np.float32)
    component_weights = {
        "eyes": 1.50,
        "nose": 1.35,
        "mouth": 0.85,
    }

    for name, mask in masks.items():
        support = mask > 0.08
        if not np.any(support):
            continue

        coarse_support = coarse[support]
        activation = float(np.percentile(coarse_support, 85))
        shape_prior = _distance_weight(mask)
        component_map = (0.40 * coarse + 0.60 * shape_prior) * mask
        component_map = _normalize_heatmap_map(component_map)
        refined += component_weights.get(name, 1.0) * activation * component_map

    if refined.max() <= 1e-6:
        return heatmap

    refined = _sparsify_heatmap(refined, percentile=50.0, gamma=0.78)
    return refined


def _extract_component_guided_heatmap(
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
        if "s_q" not in attrs or "k" not in attrs:
            continue

        s_q = attrs["s_q"]
        k = attrs["k"]

        if s_q is None or k is None:
            continue
        if s_q.ndim != 3 or k.ndim != 5:
            continue

        patch_k = k[:, :, 1:, :, :].flatten(-2).contiguous()
        syno_q = s_q.contiguous()

        syno_q = syno_q / (syno_q.norm(dim=-1, keepdim=True) + 1e-6)
        patch_k = patch_k / (patch_k.norm(dim=-1, keepdim=True) + 1e-6)

        score = torch.einsum("bqw,btpw->btqp", syno_q, patch_k)
        score = (score * 80.0).softmax(dim=-1)

        if batch_index < 0 or batch_index >= score.shape[0]:
            continue

        t_idx = time_index if time_index >= 0 else score.shape[1] + time_index
        t_idx = max(0, min(score.shape[1] - 1, t_idx))

        component_scores = score[batch_index, t_idx].detach().cpu().numpy()
        patch_num = component_scores.shape[-1]
        patch_grid = int(round(np.sqrt(patch_num)))
        if patch_grid * patch_grid != patch_num:
            continue

        component_maps = component_scores.reshape(component_scores.shape[0], patch_grid, patch_grid)
        part_names = _infer_face_part_names(component_maps.shape[0])
        priors = _build_face_component_priors(patch_grid)

        fused = np.zeros((patch_grid, patch_grid), dtype=np.float32)
        for idx, part_name in enumerate(part_names):
            cur_map = component_maps[idx].astype(np.float32)
            if part_name == "eyes":
                fused += 1.45 * (cur_map * priors["eyes"])
            elif part_name == "nose":
                fused += 1.25 * (cur_map * priors["nose"])
            elif part_name == "lips":
                fused += 0.30 * (cur_map * priors["mouth"])

        if fused.max() <= 1e-6:
            continue

        maps.append(_sparsify_heatmap(fused))

    if not maps:
        return None

    return _normalize_heatmap_map(np.stack(maps, axis=0).mean(axis=0))


def _extract_cls_patch_heatmap(
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
        maps.append(_normalize_heatmap_map(map_2d))

    if not maps:
        return None

    return _normalize_heatmap_map(np.stack(maps, axis=0).mean(axis=0))


def extract_spatial_heatmap(
    layer_attrs: Optional[List[Dict[str, Any]]],
    batch_index: int = 0,
    last_n_layers: int = 4,
    time_index: int = -1,
) -> Optional[np.ndarray]:
    component_heatmap = _extract_component_guided_heatmap(
        layer_attrs=layer_attrs,
        batch_index=batch_index,
        last_n_layers=last_n_layers,
        time_index=time_index,
    )
    if component_heatmap is not None:
        return component_heatmap

    cls_heatmap = _extract_cls_patch_heatmap(
        layer_attrs=layer_attrs,
        batch_index=batch_index,
        last_n_layers=last_n_layers,
        time_index=time_index,
    )
    if cls_heatmap is None:
        return None
    return _sparsify_heatmap(cls_heatmap, percentile=68.0, gamma=0.92)


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


def _clip_bbox_to_image(
    bbox: Tuple[float, float, float, float],
    image_shape: Tuple[int, int, int],
) -> Optional[Tuple[int, int, int, int]]:
    height, width = image_shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = int(round(max(0, min(width - 1, x1))))
    y1 = int(round(max(0, min(height - 1, y1))))
    x2 = int(round(max(x1 + 1, min(width, x2))))
    y2 = int(round(max(y1 + 1, min(height, y2))))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _expand_face_bbox(
    image_shape: Tuple[int, int, int],
    face_xywh: Tuple[int, int, int, int],
    scale: float = 1.65,
) -> Optional[Tuple[int, int, int, int]]:
    x, y, w, h = [float(v) for v in face_xywh]
    center_x = x + (w / 2.0)
    center_y = y + (h / 2.0) + (h * 0.03)
    side = max(w, h) * scale
    half = side / 2.0
    return _clip_bbox_to_image((center_x - half, center_y - half, center_x + half, center_y + half), image_shape)


def detect_primary_face_bbox(
    image_bgr: np.ndarray,
    fallback_bbox: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[Tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    detector = _load_face_detector()
    if detector is None:
        return fallback_bbox

    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(36, 36),
    )
    if len(faces) == 0:
        return fallback_bbox

    face_xywh = max(faces, key=lambda item: int(item[2]) * int(item[3]))
    return _expand_face_bbox(image_bgr.shape, tuple(int(v) for v in face_xywh))


def crop_image_to_bbox(image: np.ndarray, bbox: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
    if bbox is None:
        return image
    x1, y1, x2, y2 = bbox
    if x2 <= x1 or y2 <= y1:
        return image
    return np.ascontiguousarray(image[y1:y2, x1:x2])


def detect_and_crop_primary_face(
    image_rgb: np.ndarray,
    fallback_bbox: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[np.ndarray, Optional[Tuple[int, int, int, int]]]:
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    bbox = detect_primary_face_bbox(image_bgr, fallback_bbox=fallback_bbox)
    return crop_image_to_bbox(image_rgb, bbox), bbox


def smooth_face_bboxes(
    bboxes: List[Optional[Tuple[int, int, int, int]]],
    image_shape: Tuple[int, int, int],
    momentum: float = 0.65,
) -> List[Optional[Tuple[int, int, int, int]]]:
    smoothed: List[Optional[Tuple[int, int, int, int]]] = []
    prev_bbox: Optional[np.ndarray] = None

    for bbox in bboxes:
        if bbox is None and prev_bbox is None:
            smoothed.append(None)
            continue

        cur_bbox = prev_bbox if bbox is None else np.array(bbox, dtype=np.float32)
        if prev_bbox is None:
            blended = cur_bbox
        else:
            blended = (prev_bbox * (1.0 - momentum)) + (cur_bbox * momentum)

        clipped = _clip_bbox_to_image(tuple(float(v) for v in blended.tolist()), image_shape)
        smoothed.append(clipped)
        prev_bbox = np.array(clipped, dtype=np.float32) if clipped is not None else prev_bbox

    return smoothed


def draw_face_bbox(
    image_bgr: np.ndarray,
    bbox: Optional[Tuple[int, int, int, int]],
    label: str = "Face ROI",
) -> np.ndarray:
    out = image_bgr.copy()
    if bbox is None:
        return out
    x1, y1, x2, y2 = bbox
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 210, 255), 2)
    cv2.putText(out, label, (x1 + 4, max(26, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 210, 255), 2)
    return out


def overlay_heatmap_full(image_bgr: np.ndarray, heatmap: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    hm = cv2.resize(heatmap, (w, h), interpolation=cv2.INTER_NEAREST)
    hm_u8 = (np.clip(hm, 0.0, 1.0) * 255).astype(np.uint8)
    hm_color = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)
    blended = cv2.addWeighted(image_bgr, 1.0 - alpha, hm_color, alpha, 0.0)
    saliency = np.clip((hm - 0.35) / 0.65, 0.0, 1.0)[..., None]
    out = (
        image_bgr.astype(np.float32) * (1.0 - saliency) +
        blended.astype(np.float32) * saliency
    ).astype(np.uint8)
    return out


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
    hm = cv2.resize(heatmap, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
    hm_u8 = (np.clip(hm, 0.0, 1.0) * 255).astype(np.uint8)
    hm_color = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)
    roi = out[y1:y2, x1:x2]
    blended = cv2.addWeighted(roi, 1.0 - alpha, hm_color, alpha, 0.0)
    saliency = np.clip((hm - 0.30) / 0.70, 0.0, 1.0)[..., None]
    out[y1:y2, x1:x2] = (
        roi.astype(np.float32) * (1.0 - saliency) +
        blended.astype(np.float32) * saliency
    ).astype(np.uint8)
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 210, 255), 2)
    return out


def build_explainability_panel(
    image_bgr: np.ndarray,
    heatmap: np.ndarray,
    bbox: Optional[Tuple[int, int, int, int]] = None,
    repeat: int = 5,
    gap: int = 10,
) -> np.ndarray:
    bbox = bbox or detect_primary_face_bbox(image_bgr)
    refined_heatmap = _refine_heatmap_with_landmarks(image_bgr, heatmap, bbox)
    preview = draw_face_bbox(image_bgr, bbox)
    overlay = overlay_heatmap_on_bbox(image_bgr, refined_heatmap, bbox=bbox)
    strip = render_heatmap_strip(refined_heatmap, repeat=repeat, gap=6)

    target_h = max(image_bgr.shape[0], overlay.shape[0])
    target_w = max(image_bgr.shape[1], overlay.shape[1])
    left = cv2.resize(preview, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    right = cv2.resize(overlay, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

    top = np.full((target_h, target_w * 2 + gap, 3), 255, dtype=np.uint8)
    top[:, :target_w] = left
    top[:, target_w + gap :] = right

    cv2.putText(top, "Detected Face ROI", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (32, 32, 32), 2)
    cv2.putText(top, "Component-Focused Overlay", (target_w + gap + 12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (32, 32, 32), 2)

    strip_w = top.shape[1]
    strip_h = max(120, int(strip.shape[0] * (strip_w / max(strip.shape[1], 1))))
    strip_resized = cv2.resize(strip, (strip_w, strip_h), interpolation=cv2.INTER_NEAREST)

    title_h = 42
    bottom = np.full((strip_h + title_h, strip_w, 3), 255, dtype=np.uint8)
    cv2.putText(bottom, "Facial Component Heatmap", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (32, 32, 32), 2)
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


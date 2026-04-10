import os
import cv2
import sys
import math
import torch
import pickle
import argparse
import logging
import warnings
import numpy as np

from typing import List
from torchvision.io import VideoReader


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.utility.builtin import ODTrainer, ODLightningCLI


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Inference script for 3-model spatial heatmap comparison."
    )
    parser.add_argument("--full_cfg", type=str, required=True)
    parser.add_argument("--full_ckpt", type=str, required=True)
    parser.add_argument("--wofcg_cfg", type=str, required=True)
    parser.add_argument("--wofcg_ckpt", type=str, required=True)
    parser.add_argument("--wfcg_cfg", type=str, required=True)
    parser.add_argument("--wfcg_ckpt", type=str, required=True)
    parser.add_argument("--video_path", type=str, required=True)
    parser.add_argument("--out_dir", type=str, required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--precision", type=str, default="16")
    parser.add_argument("--batch_size", type=int, default=24)
    parser.add_argument("--heat_layers", type=int, default=4)
    parser.add_argument("--panel_cols", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.45)
    return parser.parse_args(args=args)


def configure_logging():
    logging_fmt = "[%(levelname)s][%(filename)s:%(lineno)d]: %(message)s"
    logging.basicConfig(level="INFO", format=logging_fmt)
    warnings.filterwarnings(action="ignore")


class _NumpyCompatUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.startswith("numpy._core"):
            module = module.replace("numpy._core", "numpy.core", 1)
        return super().find_class(module, name)


def _safe_pickle_load(f):
    return _NumpyCompatUnpickler(f).load()


def _normalize_bbox(bbox):
    bbox = np.asarray(bbox)
    if bbox.ndim == 1:
        bbox = bbox.reshape(2, -1)
    return bbox


def _resolve_frame_data_path(video_path):
    vid_ext = os.path.splitext(video_path)[-1]
    candidates = []

    candidates.append(
        video_path.replace("videos", "frame_data").replace(vid_ext, ".pickle")
    )

    method_alias = {
        "FS": "FaceSwap",
        "F2F": "Face2Face",
        "DF": "Deepfakes",
        "NT": "NeuralTextures",
    }
    norm_path = video_path.replace("\\", "/")
    parts = [p for p in norm_path.split("/") if p != ""]
    for i, p in enumerate(parts):
        if p == "cropped" and i + 3 < len(parts):
            method_short = parts[i + 1]
            comp = parts[i + 2]
            leaf = parts[i + 3]
            if leaf == "videos":
                method_full = method_alias.get(method_short, method_short)
                base = "/" + "/".join(parts[:i])
                filename = os.path.splitext(parts[-1])[0] + ".pickle"
                mapped = (
                    f"{base}/cropped/frame_data/{method_full}/{comp}/videos/{filename}"
                )
                candidates.append(mapped)

    for c in candidates:
        if os.path.exists(c):
            return c

    uniq = list(dict.fromkeys(candidates))
    raise FileNotFoundError(
        "Unable to locate frame_data pickle. Tried:\n  - " + "\n  - ".join(uniq)
    )


def _resolve_cropped_video_path(video_path):
    vid_ext = os.path.splitext(video_path)[-1]
    norm_path = video_path.replace("\\", "/")
    if "/cropped/" in norm_path:
        return video_path.replace(vid_ext, ".avi")
    return video_path.replace("/videos", "/cropped/videos").replace(vid_ext, ".avi")


def _build_cli(model_cfg_path, precision):
    return ODLightningCLI(
        run=False,
        trainer_class=ODTrainer,
        save_config_callback=None,
        parser_kwargs={"parser_mode": "omegaconf"},
        auto_configure_optimizers=False,
        seed_everything_default=1019,
        args=[
            "-c",
            model_cfg_path,
            "--trainer.logger=null",
            "--trainer.devices=1",
            f"--trainer.precision={precision}",
            "--model.init_args.attn_record=true",
            '--model.init_args.store_attrs=["q","k"]',
        ],
    )


def _load_model_from_ckpt(cli, ckpt_path, device):
    model = cli.model
    try:
        model = model.__class__.load_from_checkpoint(ckpt_path)
    except Exception as e:
        logging.warning(
            "Unable to load checkpoint in strict mode: %s. Falling back to strict=False.",
            e,
        )
        model = model.__class__.load_from_checkpoint(ckpt_path, strict=False)

    model.eval()
    model.to(device)
    return model

def _collect_video_data(video_path):
    vid_reader = VideoReader(video_path, "video", num_threads=1)
    fps = vid_reader.get_metadata()["video"]["fps"][0]
    frames = [fd["data"] for fd in vid_reader]
    frames = torch.stack(frames)
    del vid_reader

    resolved_frame_data_path = _resolve_frame_data_path(video_path)
    with open(resolved_frame_data_path, "rb") as f:
        fdata = _safe_pickle_load(f)
        bboxes = []
        for data in fdata:
            data["bboxes"] = [_normalize_bbox(bbox) for bbox in data["bboxes"]]
            face_idx = np.argsort(
                [np.linalg.norm((bbox[0] - bbox[1])) for bbox in data["bboxes"]]
            )[-1]
            bboxes.append(data["bboxes"][face_idx])

    cropped_video_path = _resolve_cropped_video_path(video_path)
    vid_reader = VideoReader(cropped_video_path, "video", num_threads=1)
    cropped_frames = [fd["data"] for fd in vid_reader]
    cropped_frames = torch.stack(cropped_frames)
    del vid_reader

    return {
        "fps": fps,
        "frames": frames,
        "bboxes": bboxes,
        "cropped_frames": cropped_frames,
    }


def _extract_spatial_heatmaps(layer_attrs, last_n_layers=4, time_index=-1):
    if not layer_attrs:
        return None

    maps = []
    target_layers = layer_attrs[-max(last_n_layers, 1) :]
    for attrs in target_layers:
        if not isinstance(attrs, dict):
            continue
        if ("q" not in attrs) or ("k" not in attrs):
            continue
        q = attrs["q"]
        k = attrs["k"]
        if (q is None) or (k is None):
            continue
        if (q.ndim != 5) or (k.ndim != 5):
            continue

        cls_q = q[:, :, 0, :, :]
        patch_k = k[:, :, 1:, :, :]

        cls_q = cls_q / (cls_q.norm(dim=-1, keepdim=True) + 1e-6)
        patch_k = patch_k / (patch_k.norm(dim=-1, keepdim=True) + 1e-6)

        score = torch.einsum("bthd,btphd->btph", cls_q, patch_k).mean(dim=-1)
        t_idx = time_index if time_index >= 0 else score.shape[1] + time_index
        t_idx = max(0, min(score.shape[1] - 1, t_idx))
        score = score[:, t_idx, :]
        maps.append(score)

    if len(maps) == 0:
        return None

    map_1d = torch.stack(maps, dim=0).mean(dim=0)
    map_1d = map_1d.softmax(dim=-1)

    patch_num = map_1d.shape[-1]
    patch_grid = int(round(math.sqrt(patch_num)))
    if patch_grid * patch_grid != patch_num:
        return None

    map_2d = map_1d.reshape(map_1d.shape[0], patch_grid, patch_grid)
    minv = map_2d.amin(dim=(1, 2), keepdim=True)
    maxv = map_2d.amax(dim=(1, 2), keepdim=True)
    map_2d = (map_2d - minv) / (maxv - minv + 1e-6)
    return map_2d.detach().cpu().numpy()


def _overlay_heatmap(frame_bgr, bbox, heatmap, alpha=0.45):
    out = frame_bgr.copy()
    h, w = out.shape[:2]
    p0 = bbox[0].astype(int)
    p1 = bbox[1].astype(int)

    x1 = int(np.clip(min(p0[0], p1[0]), 0, w - 1))
    y1 = int(np.clip(min(p0[1], p1[1]), 0, h - 1))
    x2 = int(np.clip(max(p0[0], p1[0]), 0, w))
    y2 = int(np.clip(max(p0[1], p1[1]), 0, h))

    if (x2 <= x1) or (y2 <= y1):
        return out

    hm = cv2.resize(heatmap, (x2 - x1, y2 - y1), interpolation=cv2.INTER_CUBIC)
    hm = np.clip(hm, 0.0, 1.0)
    hm_u8 = (hm * 255).astype(np.uint8)
    hm_color = cv2.applyColorMap(hm_u8, cv2.COLORMAP_JET)

    roi = out[y1:y2, x1:x2]
    blended = cv2.addWeighted(roi, 1.0 - alpha, hm_color, alpha, 0.0)
    out[y1:y2, x1:x2] = blended
    return out


def _draw_prediction(frame_bgr, bbox, prob, threshold):
    out = frame_bgr.copy()
    thickness = max(int(np.linalg.norm(bbox[0] - bbox[1]) * 0.01), 1)
    color = (0, 255, 0) if prob < threshold else (0, 0, 255)
    category = "REAL" if prob < threshold else "FAKE"

    out = cv2.rectangle(out, bbox[0].astype(int), bbox[1].astype(int), color, thickness)
    out = cv2.putText(
        out,
        f"{prob:.2f}",
        [int(bbox[0][0]), int(bbox[1][1] - thickness)],
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        thickness,
        cv2.LINE_AA,
    )
    out = cv2.putText(
        out,
        category,
        [int(bbox[0][0]), int(bbox[0][1] - thickness)],
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        thickness,
        cv2.LINE_AA,
    )
    return out

def _run_model_for_video(
    model,
    model_tag,
    video_data,
    batch_size,
    threshold,
    heat_layers,
    alpha,
    device,
):
    transforms = model.transform

    frames = video_data["frames"]
    bboxes = video_data["bboxes"]
    cropped_frames = video_data["cropped_frames"]
    fps = video_data["fps"]

    indices = torch.tensor(
        [int(math.floor(i * 0.333 * fps)) for i in range(10)], dtype=torch.long
    )
    start_idx = int(indices[-1].item())

    valid_total = min(len(frames), len(bboxes))
    clip_count = min(len(cropped_frames), valid_total) - start_idx
    if clip_count <= 0:
        raise ValueError(
            f"[{model_tag}] Not enough frames after temporal offset. "
            f"cropped={len(cropped_frames)}, frames={len(frames)}, bboxes={len(bboxes)}, start_idx={start_idx}"
        )

    probs: List[float] = []
    heatmaps: List[np.ndarray] = []
    i = 0
    while i < clip_count:
        cur_batch = min(clip_count - i, batch_size)
        clips = torch.stack(
            [
                transforms(cropped_frames[indices + i + j])
                for j in range(cur_batch)
            ]
        ).to(device)

        results = model.evaluate(clips)
        batch_probs = (
            results["logits"].softmax(dim=-1)[:, 1].flatten().detach().cpu().tolist()
        )
        probs.extend(batch_probs)

        layer_attrs = results.get("layer_attrs", None)
        batch_heatmaps = _extract_spatial_heatmaps(
            layer_attrs=layer_attrs, last_n_layers=heat_layers, time_index=-1
        )
        if batch_heatmaps is None:
            batch_heatmaps = np.zeros((cur_batch, 16, 16), dtype=np.float32)

        for hm in batch_heatmaps:
            heatmaps.append(hm.astype(np.float32))

        i += cur_batch

    overlays = []
    anchor_frame_indices = []
    for offset, (prob, heatmap) in enumerate(zip(probs, heatmaps)):
        fidx = start_idx + offset
        anchor_frame_indices.append(fidx)

        frame = frames[fidx].permute(1, 2, 0).numpy()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        bbox = bboxes[fidx]

        frame = _overlay_heatmap(frame, bbox, heatmap, alpha=alpha)
        frame = _draw_prediction(frame, bbox, prob, threshold=threshold)
        overlays.append(frame)

    return {
        "model_tag": model_tag,
        "fps": fps,
        "overlays": overlays,
        "probs": probs,
        "anchor_frame_indices": anchor_frame_indices,
    }


def _sample_panel_indices(length, cols):
    if length <= 0:
        return []
    if cols <= 1:
        return [length - 1]
    if length == 1:
        return [0] * cols
    return [
        int(round(i * (length - 1) / (cols - 1)))
        for i in range(cols)
    ]


def _build_panel(rows_data, row_labels, out_path, cols=5):
    clip_len = min(len(d["overlays"]) for d in rows_data)
    if clip_len <= 0:
        raise ValueError("No overlay frames available to build panel.")

    pick_idx = _sample_panel_indices(clip_len, cols)
    sample = rows_data[0]["overlays"][pick_idx[0]]
    h, w = sample.shape[:2]

    label_w = 260
    title_h = 72
    gap = 6

    canvas_h = title_h + len(rows_data) * h + (len(rows_data) - 1) * gap
    canvas_w = label_w + cols * w + (cols - 1) * gap
    canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

    for c, _ in enumerate(pick_idx):
        x = label_w + c * (w + gap)
        cv2.putText(
            canvas,
            f"t = {c + 1}",
            (x + max(8, int(w * 0.1)), 42),
            cv2.FONT_HERSHEY_TRIPLEX,
            1.0,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

    for r, (row_data, row_label) in enumerate(zip(rows_data, row_labels)):
        y = title_h + r * (h + gap)
        cv2.putText(
            canvas,
            row_label,
            (16, y + h // 2),
            cv2.FONT_HERSHEY_TRIPLEX,
            1.1,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )
        for c, idx in enumerate(pick_idx):
            x = label_w + c * (w + gap)
            canvas[y : y + h, x : x + w] = row_data["overlays"][idx]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, canvas)


def _write_video(out_path, fps, frames):
    if len(frames) == 0:
        raise ValueError(f"No frames to write for {out_path}")

    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(
        out_path,
        cv2.VideoWriter_fourcc("X", "V", "I", "D"),
        fps,
        (w, h),
    )
    for frame in frames:
        writer.write(frame)
    writer.release()

@torch.inference_mode()
def main(args):
    configure_logging()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info("Using device: %s", device)

    video_data = _collect_video_data(args.video_path)
    fps = video_data["fps"]
    logging.info(
        "Loaded video data: fps=%.3f, frames=%d, cropped_frames=%d, bboxes=%d",
        fps,
        len(video_data["frames"]),
        len(video_data["cropped_frames"]),
        len(video_data["bboxes"]),
    )

    model_specs = [
        ("full", "Full-FineTune", args.full_cfg, args.full_ckpt),
        ("wofcg", "Ours (w/o FCG)", args.wofcg_cfg, args.wofcg_ckpt),
        ("wfcg", "Ours (w/ FCG)", args.wfcg_cfg, args.wfcg_ckpt),
    ]

    videos_dir = os.path.join(args.out_dir, "videos")
    panels_dir = os.path.join(args.out_dir, "panels")
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(panels_dir, exist_ok=True)

    all_rows = []
    row_labels = []
    for model_tag, display_name, cfg_path, ckpt_path in model_specs:
        logging.info("[%s] Building CLI from config: %s", model_tag, cfg_path)
        cli = _build_cli(cfg_path, precision=args.precision)
        model = _load_model_from_ckpt(cli, ckpt_path, device=device)

        logging.info("[%s] Running inference with heatmap extraction...", model_tag)
        result = _run_model_for_video(
            model=model,
            model_tag=model_tag,
            video_data=video_data,
            batch_size=args.batch_size,
            threshold=args.threshold,
            heat_layers=args.heat_layers,
            alpha=args.alpha,
            device=device,
        )

        out_video_path = os.path.join(videos_dir, f"{model_tag}_heatmap.avi")
        _write_video(out_video_path, fps=result["fps"], frames=result["overlays"])
        logging.info("[%s] Video saved: %s", model_tag, out_video_path)

        all_rows.append(result)
        row_labels.append(display_name)

    vid_stem = os.path.splitext(os.path.basename(args.video_path))[0]
    panel_out_path = os.path.join(panels_dir, f"{vid_stem}_3x5_heatmap.png")
    _build_panel(all_rows, row_labels=row_labels, out_path=panel_out_path, cols=args.panel_cols)
    logging.info("Panel saved: %s", panel_out_path)

    logging.info("Done. Outputs in: %s", args.out_dir)


if __name__ == "__main__":
    parsed = parse_args()
    main(parsed)

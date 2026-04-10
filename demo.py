import os
import cv2
import sys
import yaml
import json
import math
import torch
import pickle
import shutil
import logging
import warnings
import argparse
import numpy as np


from os import path
from datetime import datetime
from torchvision.io import VideoReader
from src.utility.builtin import ODTrainer, ODLightningCLI


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("model_cfg_path", type=str)
    parser.add_argument("model_ckpt_path", type=str)
    parser.add_argument("video_path", type=str, nargs="+")
    parser.add_argument("--out_path", type=str, default=None)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--precision", type=str, default="16")
    parser.add_argument("--batch_size", type=int, default=30)
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search video files when an input path is a directory.",
    )
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


def _resolve_frame_data_path(video_path):
    vid_ext = os.path.splitext(video_path)[-1]
    candidates = []

    # Original legacy behavior.
    candidates.append(video_path.replace("videos", "frame_data").replace(vid_ext, ".pickle"))

    # FF++ common layout mapping:
    # cropped/<FS|F2F|DF|NT>/c23/videos -> cropped/frame_data/<FaceSwap|...>/c23/videos
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
                mapped = f"{base}/cropped/frame_data/{method_full}/{comp}/videos/{filename}"
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


def _collect_video_paths(video_inputs, recursive=False):
    video_exts = {".avi", ".mp4", ".mov", ".mkv", ".webm"}
    collected = []
    for p in video_inputs:
        if os.path.isdir(p):
            if recursive:
                walker = os.walk(p)
            else:
                walker = [(p, [], os.listdir(p))]
            for root, _, files in walker:
                for fname in files:
                    ext = os.path.splitext(fname)[-1].lower()
                    if ext in video_exts:
                        collected.append(os.path.join(root, fname))
        elif os.path.isfile(p):
            collected.append(p)
        else:
            raise FileNotFoundError(f"Input path not found: {p}")

    collected = sorted(list(dict.fromkeys(collected)))
    if len(collected) == 0:
        raise FileNotFoundError("No input videos found.")
    return collected


def _build_output_path(video_path, out_path, is_batch):
    vid_name = os.path.splitext(os.path.basename(video_path))[0]
    if not is_batch:
        return f"pred_{vid_name}.avi" if out_path is None else out_path

    out_dir = "." if out_path is None else out_path
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"pred_{vid_name}.avi")


def _normalize_bbox(bbox):
    bbox = np.asarray(bbox)
    if bbox.ndim == 1:
        bbox = bbox.reshape(2, -1)
    return bbox


@torch.inference_mode()
def demo_driver(cli, ckpt_path, video_path, out_path, batch_size, threshold):
    # setup model
    model = cli.model

    try:
        model = model.__class__.load_from_checkpoint(ckpt_path)
    except Exception as e:
        print(f"Unable to load model from checkpoint in strict mode: {e}")
        print(f"Loading model from checkpoint in non-strict mode.")
        model = model.__class__.load_from_checkpoint(ckpt_path, strict=False)

    model.eval()
    transforms = model.transform

    BATCH = batch_size
    stride = 0.333

    # load original video
    vid_reader = VideoReader(video_path, "video", num_threads=1)
    vid_ext = os.path.splitext(video_path)[-1]
    vid_name = os.path.split(video_path)[1].replace(vid_ext, "")
    fps = vid_reader.get_metadata()["video"]["fps"][0]

    frames = []
    for frame_data in vid_reader:
        frames.append(frame_data["data"])
    frames = torch.stack(frames)
    del vid_reader
    _, H, W = frames[0].shape

    # load bboxes of original video
    resolved_frame_data_path = _resolve_frame_data_path(video_path)
    with open(resolved_frame_data_path, "rb") as f:
        fdata = _safe_pickle_load(f)
        bboxes = []
        for data in fdata:
            data["bboxes"] = [
                _normalize_bbox(bbox)
                for bbox in data["bboxes"]
            ]
            face_idx = np.argsort([
                np.linalg.norm((bbox[0] - bbox[1])) for bbox in data["bboxes"]
            ])[-1]
            bboxes.append(data["bboxes"][face_idx])

    # load face cropped video
    cropped_video_path = _resolve_cropped_video_path(video_path)
    vid_reader = VideoReader(cropped_video_path, "video", num_threads=1)
    cropped_frames = []
    for frame_data in vid_reader:
        cropped_frames.append(frame_data["data"])
    cropped_frames = torch.stack(cropped_frames)
    del vid_reader

    # sample frames and inference
    indices = torch.tensor([int(math.floor(i * stride * fps)) for i in range(10)], dtype=torch.long)
    probs = []
    i = 0
    clip_count = len(cropped_frames) - indices[-1]
    while (i < clip_count):
        batch = min(clip_count - i, BATCH)
        clips = torch.stack([
            transforms(cropped_frames[indices + i + j]) for j in range(batch)
        ]).to("cuda")
        results = model.evaluate(clips)
        probs.extend(results["logits"].softmax(dim=-1)[:, 1].flatten().cpu().tolist())
        i += batch

    # draw and write to video
    bbox_frames = []
    for frame, bbox, prob in zip(frames[indices[-1]:], bboxes[indices[-1]:], probs):
        frame = frame.permute(1, 2, 0).numpy()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        thickness = int(np.linalg.norm(bbox[0] - bbox[1]) * 0.01)
        color = (0, 255, 0) if prob < threshold else (0, 0, 255)
        category = "REAL" if prob < threshold else "FAKE"
        frame = cv2.rectangle(
            frame,
            bbox[0].astype(int),
            bbox[1].astype(int),
            color,
            thickness
        )
        frame = cv2.putText(
            frame,
            f'{round(prob,2)}',
            [int(bbox[0][0]), int(bbox[1][1] - thickness)],
            cv2.FONT_HERSHEY_SIMPLEX,
            1, color, thickness, cv2.LINE_AA
        )

        frame = cv2.putText(
            frame,
            category,
            [int(bbox[0][0]), int(bbox[0][1] - thickness)],
            cv2.FONT_HERSHEY_SIMPLEX,
            1, color, thickness, cv2.LINE_AA
        )

        bbox_frames.append(frame)

    writer = cv2.VideoWriter(
        out_path,
        cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'),
        fps,
        (W, H)
    )

    for frame in bbox_frames:
        writer.write(frame)

    writer.release()


if __name__ == "__main__":
    configure_logging()

    params = parse_args()

    cli = ODLightningCLI(
        run=False,
        trainer_class=ODTrainer,
        save_config_callback=None,
        parser_kwargs={
            "parser_mode": "omegaconf"
        },
        auto_configure_optimizers=False,
        seed_everything_default=1019,
        args=[
            '-c', params.model_cfg_path,
            '--trainer.logger=null',
            f'--trainer.devices=1',
            f'--trainer.precision={params.precision}',
        ],
    )

    ckpt_path = params.model_ckpt_path
    video_paths = _collect_video_paths(params.video_path, recursive=params.recursive)
    is_batch = len(video_paths) > 1

    for i, video_path in enumerate(video_paths, start=1):
        final_out_path = _build_output_path(video_path, params.out_path, is_batch)
        print(f"[{i}/{len(video_paths)}] Processing: {video_path}")
        print(f"[{i}/{len(video_paths)}] Output: {final_out_path}")
        demo_driver(
            cli=cli,
            ckpt_path=ckpt_path,
            video_path=video_path,
            batch_size=params.batch_size,
            threshold=params.threshold,
            out_path=final_out_path
        )

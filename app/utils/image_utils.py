from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image


def load_image_rgb(image_path: Path) -> np.ndarray:
    image = Image.open(image_path).convert("RGB")
    return np.array(image)


def rgb_to_chw_uint8(image_rgb: np.ndarray) -> torch.Tensor:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("Expected RGB image with shape [H, W, 3]")
    return torch.from_numpy(image_rgb).permute(2, 0, 1)


def save_rgb_image(image_rgb: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), image_bgr)


def save_bgr_image(image_bgr: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), image_bgr)

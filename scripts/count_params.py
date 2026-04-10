import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_class(class_path: str):
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def format_count(n: int) -> str:
    return f"{n:,}"


def resolve_path_value(path_str: str, config_dir: Path) -> str:
    p = Path(path_str)
    if p.is_absolute():
        return str(p)

    cfg_candidate = (config_dir / p).resolve()
    if cfg_candidate.exists():
        return str(cfg_candidate)

    root_candidate = (PROJECT_ROOT / p).resolve()
    return str(root_candidate)


def resolve_path_args(obj: Any, config_dir: Path, key: str = "") -> Any:
    if isinstance(obj, dict):
        return {
            k: resolve_path_args(v, config_dir, key=k)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [resolve_path_args(v, config_dir, key=key) for v in obj]
    if isinstance(obj, str) and "path" in key.lower():
        return resolve_path_value(obj, config_dir)
    return obj


def main():
    parser = argparse.ArgumentParser(description="Count model parameters from config.")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to yaml config containing model.class_path and model.init_args",
    )
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if "model" not in cfg:
        raise KeyError("Config must contain `model` section.")

    model_cfg = cfg["model"]
    class_path = model_cfg.get("class_path")
    init_args = model_cfg.get("init_args", {})
    init_args = resolve_path_args(init_args, args.config.resolve().parent)

    if not class_path:
        raise KeyError("`model.class_path` is required in config.")

    model_cls = load_class(class_path)
    model = model_cls(**init_args)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params = total_params - trainable_params

    print(f"Model: {class_path}")
    print(f"Total params:     {format_count(total_params)}")
    print(f"Trainable params: {format_count(trainable_params)}")
    print(f"Frozen params:    {format_count(frozen_params)}")


if __name__ == "__main__":
    main()

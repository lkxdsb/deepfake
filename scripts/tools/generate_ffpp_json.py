"""
自动生成FF++数据集的train/val/test JSON文件

使用方法:
    python scripts/tools/generate_ffpp_json.py \
        --data-dir "E:\dataset\FaceForensics++_lq" \
        --output-dir "E:\dataset\FaceForensics++_lq\csv_files" \
        --train-ratio 0.7 \
        --val-ratio 0.15 \
        --test-ratio 0.15
"""

import os
import json
import argparse
import random
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Set


# 目录名映射：实际目录名 -> 代码期望的目录名
# 注意：脚本现在直接使用代码期望的目录名（real, DF, F2F等）
DIR_MAPPING = {
    'real': 'real',
    'DF': 'DF',
    'F2F': 'F2F',
    'FS': 'FS',
    'NT': 'NT',
    'FSh': 'FSh'
}


def scan_videos(data_dir: str, compressions: List[str] = ['c23'], vid_ext: str = '.avi'):
    """
    扫描数据集目录，收集所有视频信息
    
    返回:
        real_videos: Set[str] - 真实视频ID集合
        fake_pairs: Set[Tuple[str, str]] - 假视频对集合 (back_id, fore_id)
    """
    data_path = Path(data_dir)
    real_videos = set()
    fake_pairs = set()
    
    print("正在扫描视频文件...")
    
    # 扫描真实视频 (real目录)
    real_dir = data_path / 'real'
    if real_dir.exists():
        for comp in compressions:
            video_dir = real_dir / comp / 'videos'
            if video_dir.exists():
                for video_file in video_dir.glob(f'*{vid_ext}'):
                    video_id = video_file.stem  # 去掉扩展名
                    real_videos.add(video_id)
                print(f"  找到 {len([f for f in video_dir.glob(f'*{vid_ext}')])} 个真实视频 (compression: {comp})")
    
    # 扫描假视频 (DF, F2F, FS, NT, FSh)
    fake_dirs = ['DF', 'F2F', 'FS', 'NT', 'FSh']
    
    for fake_dir_name in fake_dirs:
        fake_dir = data_path / fake_dir_name
        if not fake_dir.exists():
            continue
        
        for comp in compressions:
            video_dir = fake_dir / comp / 'videos'
            if not video_dir.exists():
                continue
            
            count = 0
            for video_file in video_dir.glob(f'*{vid_ext}'):
                video_name = video_file.stem
                
                # 假视频命名格式通常是: back_fore.avi 或 back_fore_xxx.avi
                if '_' in video_name:
                    parts = video_name.split('_')
                    # 取前两部分作为back和fore ID
                    back_id = parts[0]
                    fore_id = parts[1]
                    fake_pairs.add((back_id, fore_id))
                    count += 1
                else:
                    print(f"  警告: 假视频文件名格式异常 ({fake_dir_name}): {video_name}")
            if count > 0:
                print(f"  找到 {count} 个假视频对 ({fake_dir_name}, compression: {comp})")
    
    print(f"\n扫描完成:")
    print(f"  真实视频数量: {len(real_videos)}")
    print(f"  假视频对数量: {len(fake_pairs)}")
    
    return real_videos, fake_pairs


def split_dataset(
    real_videos: Set[str],
    fake_pairs: Set[Tuple[str, str]],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
):
    """
    划分数据集为train/val/test
    
    返回:
        train_data, val_data, test_data: 每个都是 (real_list, fake_list) 的元组
    """
    # 验证比例
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "比例之和必须等于1"
    
    # 设置随机种子，确保可重复
    random.seed(seed)
    
    # 转换为列表并排序（确保可重复）
    real_list = sorted(list(real_videos))
    fake_list = sorted(list(fake_pairs))
    
    # 随机打乱
    random.shuffle(real_list)
    random.shuffle(fake_list)
    
    # 计算划分点
    n_real = len(real_list)
    n_fake = len(fake_list)
    
    train_real_end = int(n_real * train_ratio)
    val_real_end = train_real_end + int(n_real * val_ratio)
    
    train_fake_end = int(n_fake * train_ratio)
    val_fake_end = train_fake_end + int(n_fake * val_ratio)
    
    # 划分
    train_real = real_list[:train_real_end]
    val_real = real_list[train_real_end:val_real_end]
    test_real = real_list[val_real_end:]
    
    train_fake = fake_list[:train_fake_end]
    val_fake = fake_list[train_fake_end:val_fake_end]
    test_fake = fake_list[val_fake_end:]
    
    print(f"\n数据集划分:")
    print(f"  训练集: {len(train_real)} 真实视频, {len(train_fake)} 假视频对")
    print(f"  验证集: {len(val_real)} 真实视频, {len(val_fake)} 假视频对")
    print(f"  测试集: {len(test_real)} 真实视频, {len(test_fake)} 假视频对")
    
    return (
        (train_real, train_fake),
        (val_real, val_fake),
        (test_real, test_fake)
    )


def generate_json(real_list: List[str], fake_list: List[Tuple[str, str]]) -> List[List[str]]:
    """
    生成JSON格式的数据
    
    格式:
    [
      ["000"],           # 真实视频
      ["001", "002"],    # 假视频对
      ...
    ]
    """
    json_data = []
    
    # 添加真实视频（单个ID）
    for vid_id in real_list:
        json_data.append([vid_id])
    
    # 添加假视频对（两个ID）
    for back_id, fore_id in fake_list:
        json_data.append([back_id, fore_id])
    
    return json_data


def main():
    parser = argparse.ArgumentParser(description='生成FF++数据集的JSON文件')
    parser.add_argument(
        '--data-dir',
        type=str,
        required=True,
        help='数据集根目录（例如: E:\\dataset\\FaceForensics++_lq）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='JSON文件输出目录（默认: data_dir/csv_files）'
    )
    parser.add_argument(
        '--compressions',
        type=str,
        nargs='+',
        default=['c23'],
        help='压缩质量列表（例如: c23 c40 raw）'
    )
    parser.add_argument(
        '--vid-ext',
        type=str,
        default='.avi',
        help='视频文件扩展名（默认: .avi）'
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.7,
        help='训练集比例（默认: 0.7）'
    )
    parser.add_argument(
        '--val-ratio',
        type=float,
        default=0.15,
        help='验证集比例（默认: 0.15）'
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=0.15,
        help='测试集比例（默认: 0.15）'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='随机种子（默认: 42）'
    )
    
    args = parser.parse_args()
    
    # 设置输出目录
    if args.output_dir is None:
        output_dir = Path(args.data_dir) / 'csv_files'
    else:
        output_dir = Path(args.output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"数据集目录: {args.data_dir}")
    print(f"输出目录: {output_dir}")
    print(f"压缩质量: {args.compressions}")
    print(f"视频扩展名: {args.vid_ext}")
    print(f"划分比例: Train={args.train_ratio}, Val={args.val_ratio}, Test={args.test_ratio}")
    print("-" * 60)
    
    # 扫描视频
    real_videos, fake_pairs = scan_videos(
        args.data_dir,
        args.compressions,
        args.vid_ext
    )
    
    if len(real_videos) == 0 and len(fake_pairs) == 0:
        print("错误: 未找到任何视频文件！")
        return
    
    # 划分数据集
    train_data, val_data, test_data = split_dataset(
        real_videos,
        fake_pairs,
        args.train_ratio,
        args.val_ratio,
        args.test_ratio,
        args.seed
    )
    
    # 生成JSON文件
    print("\n正在生成JSON文件...")
    
    # Train
    train_json = generate_json(train_data[0], train_data[1])
    train_path = output_dir / 'train.json'
    with open(train_path, 'w', encoding='utf-8') as f:
        json.dump(train_json, f, indent=2, ensure_ascii=False)
    print(f"  ✓ 已生成: {train_path} ({len(train_json)} 个条目)")
    
    # Val
    val_json = generate_json(val_data[0], val_data[1])
    val_path = output_dir / 'val.json'
    with open(val_path, 'w', encoding='utf-8') as f:
        json.dump(val_json, f, indent=2, ensure_ascii=False)
    print(f"  ✓ 已生成: {val_path} ({len(val_json)} 个条目)")
    
    # Test
    test_json = generate_json(test_data[0], test_data[1])
    test_path = output_dir / 'test.json'
    with open(test_path, 'w', encoding='utf-8') as f:
        json.dump(test_json, f, indent=2, ensure_ascii=False)
    print(f"  ✓ 已生成: {test_path} ({len(test_json)} 个条目)")
    
    print("\n" + "=" * 60)
    print("完成！JSON文件已生成。")
    print(f"文件位置: {output_dir}")
    print("\n提示:")
    print("1. 确保JSON文件中的视频ID与实际的视频文件名匹配")
    print("2. 假视频文件命名格式应为: back_id_fore_id.avi")
    print("3. 如果使用不同的目录结构，可能需要调整代码中的目录映射")


if __name__ == "__main__":
    main()


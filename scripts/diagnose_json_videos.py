#!/usr/bin/env python3
"""
诊断 JSON 文件和视频文件的匹配问题
"""
import json
import os
from pathlib import Path
from os import path

def check_json_video_match(data_dir, split='train'):
    """检查 JSON 文件中的 ID 是否与实际视频文件匹配"""
    
    # 读取 JSON 文件
    json_path = path.join(data_dir, 'csv_files', f'{split}.json')
    if not path.exists(json_path):
        print(f"❌ JSON 文件不存在: {json_path}")
        return
    
    with open(json_path, 'r') as f:
        idxs = json.load(f)
    
    print(f"✅ 读取 JSON 文件: {json_path}")
    print(f"   JSON 条目数: {len(idxs)}")
    print()
    
    # 检查 REAL 视频
    print("=" * 60)
    print("检查 REAL 视频:")
    print("=" * 60)
    real_dir = path.join(data_dir, 'real', 'c23', 'videos')
    if path.exists(real_dir):
        real_files = [f.name.replace('.avi', '') for f in os.scandir(real_dir) if f.name.endswith('.avi')]
        real_files_set = set(real_files)
        print(f"   REAL 视频目录: {real_dir}")
        print(f"   实际文件数: {len(real_files)}")
        print(f"   前 10 个文件名: {real_files[:10]}")
        
        # 从 JSON 中提取 REAL 视频 ID
        real_ids = [i for inner in idxs for i in inner if len(inner) == 1]
        real_ids_set = set(real_ids)
        print(f"   JSON 中的 REAL ID 数: {len(real_ids)}")
        print(f"   前 10 个 JSON ID: {real_ids[:10]}")
        
        # 检查匹配
        matched = real_ids_set & real_files_set
        missing_in_files = real_ids_set - real_files_set
        missing_in_json = real_files_set - real_ids_set
        
        print(f"\n   ✅ 匹配的 ID: {len(matched)}")
        if missing_in_files:
            print(f"   ❌ JSON 中有但文件不存在 (前 20 个): {list(missing_in_files)[:20]}")
        if missing_in_json:
            print(f"   ⚠️  文件存在但 JSON 中没有 (前 20 个): {list(missing_in_json)[:20]}")
    else:
        print(f"   ❌ REAL 视频目录不存在: {real_dir}")
    
    print()
    
    # 检查 FAKE 视频 (DF)
    print("=" * 60)
    print("检查 FAKE 视频 (DF):")
    print("=" * 60)
    df_dir = path.join(data_dir, 'DF', 'c23', 'videos')
    if path.exists(df_dir):
        df_files = [f.name.replace('.avi', '') for f in os.scandir(df_dir) if f.name.endswith('.avi')]
        df_files_set = set(df_files)
        print(f"   DF 视频目录: {df_dir}")
        print(f"   实际文件数: {len(df_files)}")
        print(f"   前 10 个文件名: {df_files[:10]}")
        
        # 从 JSON 中提取 FAKE 视频 ID (配对)
        fake_pairs = [idx for idx in idxs if len(idx) == 2]
        print(f"   JSON 中的 FAKE 配对数: {len(fake_pairs)}")
        if fake_pairs:
            print(f"   前 5 个配对: {fake_pairs[:5]}")
        
        # 生成所有可能的 ID (包括反向)
        fake_ids = []
        for pair in fake_pairs:
            fake_ids.append('_'.join(pair))
            fake_ids.append('_'.join(reversed(pair)))
        fake_ids_set = set(fake_ids)
        print(f"   生成的 FAKE ID 数 (包括反向): {len(fake_ids_set)}")
        print(f"   前 10 个生成的 ID: {list(fake_ids_set)[:10]}")
        
        # 检查匹配
        matched = fake_ids_set & df_files_set
        missing_in_files = fake_ids_set - df_files_set
        missing_in_json = df_files_set - fake_ids_set
        
        print(f"\n   ✅ 匹配的 ID: {len(matched)}")
        if missing_in_files:
            print(f"   ❌ JSON 中有但文件不存在 (前 20 个): {list(missing_in_files)[:20]}")
        if missing_in_json:
            print(f"   ⚠️  文件存在但 JSON 中没有 (前 20 个): {list(missing_in_json)[:20]}")
    else:
        print(f"   ❌ DF 视频目录不存在: {df_dir}")
    
    print()
    print("=" * 60)
    print("总结:")
    print("=" * 60)
    print("如果看到很多 'JSON 中有但文件不存在'，说明 JSON 文件中的 ID 与实际文件名不匹配")
    print("需要根据实际文件名更新 JSON 文件")

if __name__ == '__main__':
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else '/root/autodl-tmp/dataset/cropped'
    split = sys.argv[2] if len(sys.argv) > 2 else 'train'
    
    check_json_video_match(data_dir, split)


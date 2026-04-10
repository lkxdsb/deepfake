#!/usr/bin/env python3
"""
检查缓存文件的内容，看看是否包含所有视频
"""
import pickle
import os
import sys
from pathlib import Path

def check_cache_content(data_dir):
    """检查缓存文件的内容"""
    
    cache_dir = os.path.expanduser('./.cache')
    
    if not os.path.exists(cache_dir):
        print(f"❌ 缓存目录不存在: {cache_dir}")
        return
    
    print("=" * 70)
    print("检查缓存文件内容")
    print("=" * 70)
    print(f"缓存目录: {os.path.abspath(cache_dir)}")
    print()
    
    # 检查所有缓存文件
    cache_files = [f for f in os.listdir(cache_dir) if f.startswith('FFPP-') and f.endswith('.pkl')]
    
    if not cache_files:
        print("❌ 没有找到缓存文件")
        return
    
    print(f"找到 {len(cache_files)} 个缓存文件:\n")
    
    for cache_file in sorted(cache_files):
        cache_path = os.path.join(cache_dir, cache_file)
        print("-" * 70)
        print(f"缓存文件: {cache_file}")
        print(f"完整路径: {os.path.abspath(cache_path)}")
        print(f"文件大小: {os.path.getsize(cache_path) / 1024:.1f} KB")
        
        try:
            with open(cache_path, 'rb') as f:
                video_metas = pickle.load(f)
            
            print(f"包含视频数: {len(video_metas)}")
            
            if len(video_metas) > 0:
                print(f"前 10 个视频 ID:")
                for i, vid_id in enumerate(list(video_metas.keys())[:10]):
                    meta = video_metas[vid_id]
                    print(f"  {i+1}. {vid_id}: fps={meta.get('fps', 'N/A')}, "
                          f"duration={meta.get('duration', 'N/A'):.2f}s, "
                          f"frames={meta.get('frames', 'N/A')}")
                
                # 检查实际文件
                # 从文件名解析类型和压缩格式
                # FFPP-REAL-c23.pkl -> REAL, c23
                parts = cache_file.replace('FFPP-', '').replace('.pkl', '').split('-')
                if len(parts) >= 2:
                    df_type = parts[0]
                    comp = parts[1]
                    
                    video_dir = os.path.join(data_dir, 
                                           'real' if df_type == 'REAL' else df_type,
                                           comp, 'videos')
                    
                    if os.path.exists(video_dir):
                        actual_files = set([f.name.replace('.avi', '') 
                                          for f in os.scandir(video_dir) 
                                          if f.name.endswith('.avi')])
                        cache_ids = set(video_metas.keys())
                        
                        matched = actual_files & cache_ids
                        missing_in_cache = actual_files - cache_ids
                        extra_in_cache = cache_ids - actual_files
                        
                        print(f"\n与实际文件对比:")
                        print(f"  实际文件数: {len(actual_files)}")
                        print(f"  缓存中的 ID 数: {len(cache_ids)}")
                        print(f"  ✅ 匹配数: {len(matched)}")
                        
                        if missing_in_cache:
                            print(f"  ❌ 文件存在但缓存中没有: {len(missing_in_cache)} 个")
                            print(f"     前 20 个: {list(missing_in_cache)[:20]}")
                        
                        if extra_in_cache:
                            print(f"  ⚠️  缓存中有但文件不存在: {len(extra_in_cache)} 个")
                            print(f"     前 20 个: {list(extra_in_cache)[:20]}")
                    else:
                        print(f"\n⚠️  视频目录不存在: {video_dir}")
            else:
                print("  ⚠️  缓存文件为空！")
                
        except Exception as e:
            print(f"  ❌ 读取缓存文件时出错: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 70)
    print("总结:")
    print("=" * 70)
    print("如果看到 '文件存在但缓存中没有'，说明缓存文件不完整")
    print("建议运行: python scripts/regenerate_cache.py <data_dir> --force")
    print()
    print("缓存文件位置:")
    print(f"  {os.path.abspath(cache_dir)}")

if __name__ == '__main__':
    data_dir = sys.argv[1] if len(sys.argv) > 1 else '/root/autodl-tmp/dataset/cropped'
    check_cache_content(data_dir)


#!/usr/bin/env python3
"""
重新生成视频元数据缓存文件
这个脚本会扫描所有视频文件，读取元数据（fps, duration, frames），
然后生成缓存文件到 ./.cache/ 目录
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入需要的类，避免导入整个模块链
from src.dataset.base import DeepFakeDataset

def regenerate_cache(data_dir, compressions=['c23'], vid_ext='.avi', force=False):
    """重新生成缓存文件"""
    
    print("=" * 70)
    print("重新生成视频元数据缓存文件")
    print("=" * 70)
    print(f"数据目录: {data_dir}")
    print(f"压缩格式: {compressions}")
    print(f"视频扩展名: {vid_ext}")
    print()
    
    # 检查缓存目录
    cache_dir = os.path.expanduser('./.cache')
    print(f"缓存目录: {cache_dir}")
    
    # 检查现有缓存文件
    existing_caches = []
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            if f.startswith('FFPP-') and f.endswith('.pkl'):
                cache_file = os.path.join(cache_dir, f)
                existing_caches.append(cache_file)
    
    if existing_caches and not force:
        print(f"\n⚠️  发现 {len(existing_caches)} 个现有缓存文件:")
        for cache in existing_caches:
            size = os.path.getsize(cache) / 1024
            print(f"   - {os.path.basename(cache)} ({size:.1f} KB)")
        print("\n这些文件将被更新（如果视频文件存在）")
        print("如果视频文件已被删除，缓存中的旧条目将被移除")
        print()
        cont = input("继续? (y/n): ")
        if cont.lower() != 'y':
            print("已取消")
            return False
        # 删除旧缓存文件，强制重新生成
        print("\n删除旧缓存文件以强制重新生成...")
        for cache in existing_caches:
            os.remove(cache)
            print(f"   已删除: {os.path.basename(cache)}")
        print()
    elif force:
        print("\n强制模式：将重新生成所有缓存文件")
        if existing_caches:
            print("删除旧缓存文件...")
            for cache in existing_caches:
                os.remove(cache)
                print(f"   已删除: {os.path.basename(cache)}")
        print()
    else:
        # 即使没有 --force，也删除现有缓存以确保重新生成
        if existing_caches:
            print("\n删除现有缓存文件以确保重新生成...")
            for cache in existing_caches:
                os.remove(cache)
                print(f"   已删除: {os.path.basename(cache)}")
        print()
    
    # 确保缓存目录存在
    os.makedirs(cache_dir, exist_ok=True)
    
    # 生成新缓存
    print("开始生成缓存文件...")
    print("这可能需要一些时间，请耐心等待...")
    print("(会扫描所有视频文件并读取元数据)")
    print()
    
    try:
        # 直接调用 prepare_data，避免导入 FFPP 的完整依赖
        # 使用 DeepFakeDataset 的静态方法
        from src.dataset.ffpp import FFPP
        FFPP.prepare_data(data_dir, compressions, vid_ext)
        print()
        print("=" * 70)
        print("✅ 缓存文件生成完成！")
        print("=" * 70)
        print()
        
        # 显示生成的缓存文件并检查内容
        if os.path.exists(cache_dir):
            new_caches = [f for f in os.listdir(cache_dir) if f.startswith('FFPP-') and f.endswith('.pkl')]
            if new_caches:
                print("生成的缓存文件:")
                total_videos = 0
                for cache in sorted(new_caches):
                    cache_path = os.path.join(cache_dir, cache)
                    size = os.path.getsize(cache_path) / 1024  # KB
                    
                    # 检查缓存文件内容
                    try:
                        import pickle
                        with open(cache_path, 'rb') as f:
                            video_metas = pickle.load(f)
                        video_count = len(video_metas)
                        total_videos += video_count
                        print(f"   - {cache} ({size:.1f} KB, {video_count} 个视频)")
                    except Exception as e:
                        print(f"   - {cache} ({size:.1f} KB, 读取失败: {e})")
                
                print(f"\n总计: {total_videos} 个视频的元数据")
                
                if total_videos == 0:
                    print("\n⚠️  警告: 所有缓存文件都是空的！")
                    print("   可能的原因:")
                    print("   1. 视频文件路径不正确")
                    print("   2. 视频文件损坏或格式不支持")
                    print("   3. 视频文件扩展名不匹配")
                    print("\n   请检查:")
                    print(f"   - 数据目录: {data_dir}")
                    print(f"   - 视频扩展名: {vid_ext}")
                    print(f"   - 压缩格式: {compressions}")
            else:
                print("⚠️  没有生成任何缓存文件！")
        
        print()
        print("现在可以重新运行训练脚本了")
        return True
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ 生成缓存时出错: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='重新生成视频元数据缓存文件')
    parser.add_argument('data_dir', type=str, 
                       help='数据目录路径 (例如: /root/autodl-tmp/dataset/cropped)')
    parser.add_argument('--compressions', type=str, default='c23',
                       help='压缩格式，多个用逗号分隔 (默认: c23)')
    parser.add_argument('--vid-ext', type=str, default='.avi',
                       help='视频文件扩展名 (默认: .avi)')
    parser.add_argument('--force', action='store_true',
                       help='强制重新生成，删除旧缓存')
    
    args = parser.parse_args()
    
    compressions = [c.strip() for c in args.compressions.split(',')]
    
    regenerate_cache(
        args.data_dir, 
        compressions, 
        args.vid_ext,
        force=args.force
    )


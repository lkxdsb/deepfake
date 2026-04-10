#!/usr/bin/env python
"""
检查 PyAV 库是否正确安装和工作

使用方法：
python check_pyav.py
"""
import sys

def check_pyav():
    print("=" * 60)
    print("检查 PyAV 库状态")
    print("=" * 60)
    
    # 1. 检查是否可以导入
    print("\n1. 检查 PyAV 导入...")
    try:
        import av
        print(f"   ✅ PyAV 已安装，版本: {av.__version__}")
    except ImportError as e:
        print(f"   ❌ PyAV 未安装: {e}")
        print("\n   解决方案：")
        print("   pip install av")
        return False
    except Exception as e:
        print(f"   ❌ PyAV 导入失败: {e}")
        return False
    
    # 2. 检查 av.open 是否可用
    print("\n2. 检查 av.open 方法...")
    try:
        if hasattr(av, 'open'):
            print("   ✅ av.open 方法存在")
        else:
            print("   ❌ av.open 方法不存在")
            return False
    except Exception as e:
        print(f"   ❌ 检查 av.open 失败: {e}")
        return False
    
    # 3. 检查 torchvision.io.VideoReader
    print("\n3. 检查 torchvision.io.VideoReader...")
    try:
        from torchvision.io import VideoReader
        print("   ✅ VideoReader 可以导入")
    except ImportError as e:
        print(f"   ❌ VideoReader 导入失败: {e}")
        return False
    except Exception as e:
        print(f"   ❌ VideoReader 检查失败: {e}")
        return False
    
    # 4. 测试读取一个视频文件（如果提供）
    if len(sys.argv) > 1:
        test_video = sys.argv[1]
        print(f"\n4. 测试读取视频文件: {test_video}")
        try:
            from torchvision.io import VideoReader
            reader = VideoReader(test_video, "video")
            metadata = reader.get_metadata()
            print(f"   ✅ 成功读取视频")
            print(f"   FPS: {metadata['video']['fps']}")
            print(f"   Duration: {metadata['video']['duration']}")
        except Exception as e:
            print(f"   ❌ 读取视频失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ PyAV 检查完成，所有测试通过！")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = check_pyav()
    sys.exit(0 if success else 1)


# 预处理脚本GPU需求说明

## 📊 总结

| 文件 | 是否需要GPU | 说明 |
|------|-----------|------|
| `fetch_landmark_bbox.py` | ✅ **需要** | 使用face_alignment库进行人脸关键点检测 |
| `crop_main_face.py` | ❌ **不需要** | 仅使用cv2和numpy进行图像处理 |
| `show_frame_landmark_bbox.py` | ❌ **不需要** | 可视化工具，仅用于显示 |
| `robustness/phase1_apply_all_to_videos.py` | ❌ **不需要** | 视频扰动处理，仅使用cv2 |
| `robustness/phase2_face_crop_all_videos.py` | ❌ **不需要** | 调用crop_main_face，不需要GPU |

## 🔍 详细说明

### 1. `fetch_landmark_bbox.py` - **需要GPU** ⚠️

**原因：**
- 使用了 `face_alignment` 库进行2D人脸关键点检测
- 代码中明确设置了 `device="cuda"`（第109行）
- 使用PyTorch进行推理

**代码片段：**
```python
model = face_alignment.FaceAlignment(
    face_alignment.LandmarksType.TWO_D,
    face_detector='sfd',
    dtype=torch.float16,
    flip_input=False,
    device="cuda",  # ← 这里明确使用GPU
)
```

**如果没有GPU怎么办？**
可以修改代码，将 `device="cuda"` 改为 `device="cpu"`，但速度会非常慢。

### 2. `crop_main_face.py` - **不需要GPU** ✅

**原因：**
- 只使用了 `cv2`（OpenCV）和 `numpy` 进行图像处理
- 主要功能是：
  - 读取之前提取的landmark数据
  - 进行人脸对齐和裁剪
  - 保存裁剪后的视频

**依赖：**
- OpenCV (cv2)
- NumPy
- 多进程处理（使用CPU多核）

### 3. `show_frame_landmark_bbox.py` - **不需要GPU** ✅

**原因：**
- 仅用于可视化，显示landmark和bbox
- 使用matplotlib进行绘图

### 4. `robustness/phase1_apply_all_to_videos.py` - **不需要GPU** ✅

**原因：**
- 对视频应用各种扰动（模糊、噪声、压缩等）
- 只使用cv2和图像处理库
- 可以多进程并行处理（使用CPU）

### 5. `robustness/phase2_face_crop_all_videos.py` - **不需要GPU** ✅

**原因：**
- 调用 `crop_main_face.py` 的main函数
- 本身不进行GPU计算

## 💡 使用建议

### 标准预处理流程

1. **第一步：提取landmark**（需要GPU）
   ```bash
   python -m src.preprocess.fetch_landmark_bbox \
       --root-dir="你的数据集目录" \
       --video-dir="videos" \
       --fdata-dir="frame_data" \
       --batch=1
   ```
   ⚠️ **这一步必须在有GPU的机器上运行**

2. **第二步：裁剪人脸**（不需要GPU）
   ```bash
   python -m src.preprocess.crop_main_face \
       --root-dir="你的数据集目录" \
       --video-dir="videos" \
       --fdata-dir="frame_data" \
       --crop-dir="cropped" \
       --workers=8  # 可以使用多核CPU加速
   ```
   ✅ **这一步可以在没有GPU的机器上运行，使用多核CPU即可**

### 如果没有GPU怎么办？

**选项1：修改代码使用CPU**（不推荐，非常慢）
```python
# 在 fetch_landmark_bbox.py 第109行
device="cpu",  # 改为cpu，但速度会慢很多
```

**选项2：使用云GPU服务**
- Google Colab（免费GPU）
- AWS EC2 GPU实例
- 阿里云GPU服务器

**选项3：只运行第一步在GPU机器上**
- 在有GPU的机器上运行 `fetch_landmark_bbox.py`
- 将生成的 `frame_data` 文件夹复制到其他机器
- 在其他机器上运行 `crop_main_face.py`（不需要GPU）

## 📝 注意事项

1. **`fetch_landmark_bbox.py` 是唯一需要GPU的脚本**
   - 如果数据集很大，这一步可能需要较长时间
   - 建议使用batch_size=1（代码默认值）

2. **其他脚本都可以在CPU上运行**
   - `crop_main_face.py` 可以使用多进程加速（`--workers` 参数）
   - 建议workers数量 = CPU核心数 / 2

3. **内存需求**
   - `fetch_landmark_bbox.py`：需要足够的GPU显存（建议至少4GB）
   - `crop_main_face.py`：需要足够的系统内存（取决于视频大小和workers数量）

## 🔧 检查GPU是否可用

运行以下命令检查：
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU device: {torch.cuda.get_device_name(0)}")
```


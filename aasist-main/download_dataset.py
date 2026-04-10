"""
AASIST
Copyright (c) 2021-present NAVER Corp.
MIT license
修改说明：替换系统curl/unzip命令为Python内置模块，解决Windows兼容性问题
"""

import os
import requests
import zipfile
from tqdm import tqdm  # 用于显示下载进度（可选，提升体验）

def download_file(url, save_path):
    """
    用Python内置requests下载文件，带进度条，替代curl命令
    :param url: 下载链接
    :param save_path: 保存路径（含文件名）
    """
    # 避免重复下载
    if os.path.exists(save_path):
        print(f"文件 {save_path} 已存在，跳过下载")
        return True
    
    try:
        # 发送GET请求，流式下载（避免内存溢出）
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()  # 检查请求是否成功
        
        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0))
        
        # 显示下载进度条
        with open(save_path, 'wb') as f, tqdm(
            desc=os.path.basename(save_path),
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        print(f"下载完成：{save_path}")
        return True
    except Exception as e:
        print(f"下载失败：{e}")
        # 删除损坏的文件
        if os.path.exists(save_path):
            os.remove(save_path)
        return False

def unzip_file(zip_path, extract_path="."):
    """
    用Python内置zipfile解压文件，替代unzip命令
    :param zip_path: 压缩包路径
    :param extract_path: 解压目标路径
    """
    if not os.path.exists(zip_path):
        print(f"压缩包 {zip_path} 不存在，解压失败")
        return False
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 显示解压进度
            for member in tqdm(zip_ref.infolist(), desc="解压中"):
                zip_ref.extract(member, extract_path)
        print(f"解压完成：{zip_path} -> {extract_path}")
        return True
    except zipfile.BadZipFile:
        print(f"压缩包损坏：{zip_path}")
        return False
    except Exception as e:
        print(f"解压失败：{e}")
        return False

if __name__ == "__main__":
    # 数据集下载链接（去掉多余的转义符，原始合法URL）
    dataset_url = "https://datashare.ed.ac.uk/bitstream/handle/10283/3336/LA.zip?sequence=3&isAllowed=y"
    zip_save_path = "./LA.zip"
    
    # 1. 下载数据集（替代原curl命令）
    download_success = download_file(dataset_url, zip_save_path)
    
    # 2. 解压数据集（替代原unzip命令）
    if download_success:
        unzip_file(zip_save_path)
        
        # 可选：解压后删除压缩包（节省空间）
        # os.remove(zip_save_path)
        # print("已删除压缩包 LA.zip")
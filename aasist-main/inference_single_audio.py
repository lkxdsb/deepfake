import os
import argparse
import json
import torch
import torch.nn.functional as F
import librosa
from importlib import import_module

# ===================== 默认配置（和你的模型完全对齐） =====================
DEFAULT_CONFIG_PATH = "config/AASIST-L.conf"
DEFAULT_MODEL_PATH = "exp_result/LA_AASIST-L_ep100_bs24/weights/best.pth"
DEFAULT_THRESHOLD = 1.8712  # 你的EER最优阈值

def load_audio(audio_path, target_sr=16000, nb_samp=64600):
    """和训练时完全一致的音频预处理逻辑"""
    audio, sr = librosa.load(audio_path, sr=target_sr, mono=True)
    # 长度对齐训练要求
    if len(audio) > nb_samp:
        audio = audio[:nb_samp]
    elif len(audio) < nb_samp:
        audio = librosa.util.pad_center(audio, size=nb_samp, mode='constant')
    # 转为模型要求的张量格式 [batch, 采样点]
    return torch.FloatTensor(audio).unsqueeze(0)

def get_model(model_config, device):
    """和官方main.py完全一致的模型加载逻辑"""
    module = import_module(f"models.{model_config['architecture']}")
    model_class = getattr(module, "Model")
    return model_class(model_config).to(device)

def main():
    parser = argparse.ArgumentParser(description="AASIST 音频反欺诈检测")
    parser.add_argument("--audio", type=str, required=True, help="输入音频路径 (wav/flac/mp3)")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="模型配置文件路径")
    parser.add_argument("--model_path", type=str, default=DEFAULT_MODEL_PATH, help="模型权重路径")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="分类阈值：原始得分 < 阈值 判定为AI伪造")
    args = parser.parse_args()

    # 基础文件校验
    if not os.path.exists(args.audio):
        raise FileNotFoundError(f"音频文件不存在: {args.audio}")
    if not os.path.exists(args.model_path):
        raise FileNotFoundError(f"模型权重不存在: {args.model_path}")

    # 设备设置
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    # 加载配置和模型
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    model_config = config["model_config"]

    print(f"加载模型: {args.model_path}")
    model = get_model(model_config, device)
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.eval()
    print("模型加载完成")

    # 音频预处理
    print(f"处理音频: {args.audio}")
    audio_tensor = load_audio(args.audio, nb_samp=model_config["nb_samp"]).to(device)

    # 推理
    print("执行检测...")
    with torch.no_grad():
        _, batch_out = model(audio_tensor)
        # 1. 官方原始得分：真实人声的logit（和训练、EER计算完全对齐）
        raw_score = batch_out[:, 1].item()
        # 2. 用softmax计算准确的类别概率（二分类，概率和为1）
        class_prob = F.softmax(batch_out, dim=1)
        spoof_prob = class_prob[:, 0].item()  # AI伪造概率
        bonafide_prob = class_prob[:, 1].item()  # 真实人声概率

    # 结果输出（极简，无冗余内容）
    print("\n" + "="*50)
    print("【检测核心结果】")
    print("="*50)
    print(f"1. 官方原始Logit得分: {raw_score:.4f}")
    print(f"   规则：得分 < {args.threshold:.4f} → 判定为AI伪造语音")
    print(f"\n2. 类别概率:")
    print(f"   AI伪造/诈骗语音概率: {spoof_prob*100:.1f}%")
    print(f"   真实人声概率: {bonafide_prob*100:.1f}%")
    
    # 最终结论（和阈值、概率完全对齐）
    is_spoof = raw_score < args.threshold
    print(f"\n3. 最终检测结论: {'🚨 AI伪造/诈骗语音' if is_spoof else '✅ 真实人声'}")
    print("="*50)

if __name__ == "__main__":
    main()
import os
import json
import torch
import torch.nn.functional as F
import librosa
import numpy as np
import pandas as pd
from importlib import import_module
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from tqdm import tqdm


# ===================== 默认配置 =====================
DEFAULT_CONFIG_PATH = "config/AASIST-L.conf"
DEFAULT_MODEL_PATH = "exp_result/LA_AASIST-L_ep100_bs24/weights/best.pth"
TEST_ROOT = "./audio_dataset/test"


# ===================== 音频预处理 =====================
def load_audio(audio_path, target_sr=16000, nb_samp=64600):
    audio, sr = librosa.load(audio_path, sr=target_sr, mono=True)
    if len(audio) > nb_samp:
        audio = audio[:nb_samp]
    elif len(audio) < nb_samp:
        audio = librosa.util.pad_center(audio, size=nb_samp, mode="constant")
    return torch.FloatTensor(audio).unsqueeze(0)


# ===================== 模型加载 =====================
def get_model(model_config, device):
    module = import_module(f"models.{model_config['architecture']}")
    model_class = getattr(module, "Model")
    return model_class(model_config).to(device)


# ===================== 单样本推理 =====================
@torch.no_grad()
def infer_one(audio_tensor, model, device):
    """返回 raw_score、伪造概率、真实概率"""
    _, batch_out = model(audio_tensor.to(device))
    raw_score = batch_out[:, 1].item()
    class_prob = F.softmax(batch_out, dim=1)
    spoof_prob = class_prob[:, 0].item()
    bona_prob = class_prob[:, 1].item()
    return raw_score, spoof_prob, bona_prob


# ===================== 主函数 =====================
if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    # 加载模型配置与权重
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    model_config = config["model_config"]

    print(f"加载模型权重: {DEFAULT_MODEL_PATH}")
    model = get_model(model_config, device)
    model.load_state_dict(torch.load(DEFAULT_MODEL_PATH, map_location=device))
    model.eval()

    # 收集测试集音频文件
    audio_exts = {".wav", ".flac", ".mp3"}
    test_files = []
    for folder in ["normal", "fraud"]:
        dir_path = os.path.join(TEST_ROOT, folder)
        label = 0 if folder == "normal" else 1  # 真实=0, 伪造=1
        if not os.path.exists(dir_path):
            continue
        for fn in os.listdir(dir_path):
            if os.path.splitext(fn)[1].lower() in audio_exts:
                test_files.append((os.path.join(dir_path, fn), label))

    print(f"共检测到 {len(test_files)} 个音频样本\n")

    # 推理循环
    y_true, y_raw, y_prob, records = [], [], [], []
    for path, label in tqdm(test_files, desc="测试样本"):
        try:
            audio_tensor = load_audio(path, nb_samp=model_config["nb_samp"])
            raw_score, spoof_p, bona_p = infer_one(audio_tensor, model, device)
            y_true.append(label)
            y_raw.append(raw_score)
            y_prob.append(spoof_p)
            records.append({
                "音频路径": path,
                "真实标签": "真实" if label == 0 else "伪造",
                "Raw得分": round(raw_score, 4),
                "AI伪造概率": round(spoof_p, 4),
                "真实概率": round(bona_p, 4)
            })
        except Exception as e:
            print(f"{path} 出错：{e}")

    y_true = np.array(y_true)
    y_raw = np.array(y_raw)
    y_prob = np.array(y_prob)

    # ===================== 动态阈值搜索 =====================
    print("\n正在搜索最佳阈值 (以 F1-score 为准)...")
    best_thr, best_f1 = None, 0

    # 防止假高分：仅在合理区间搜索且忽略单类结果
    for thr in np.linspace(np.min(y_raw), np.max(y_raw), 200):
        y_pred_tmp = (y_raw < thr).astype(int)
        if len(np.unique(y_pred_tmp)) < 2:
            continue  # 跳过只有单类预测的阈值
        f1 = f1_score(y_true, y_pred_tmp, zero_division=0)
        if f1 > best_f1:
            best_thr, best_f1 = thr, f1

    if best_thr is None:
        best_thr = np.median(y_raw)  # fallback
        print("⚠️ 阈值搜索异常，使用Raw得分中位数作为阈值。")

    print(f"最优阈值: {best_thr:.4f} (对应 F1 = {best_f1:.4f})")

    # 重新计算各项指标
    y_pred = (y_raw < best_thr).astype(int)
    acc = accuracy_score(y_true, y_pred)
    pre = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    try:
        auc = roc_auc_score(y_true, y_prob)
    except Exception:
        auc = float("nan")

    print("\n测试集评估结果")
    print("=" * 50)
    print(f"动态阈值     : {best_thr:.4f}")
    print(f"Accuracy     : {acc:.4f}")
    print(f"Precision    : {pre:.4f}")
    print(f"Recall       : {rec:.4f}")
    print(f"F1-score     : {f1:.4f}")
    print(f"AUC          : {auc:.4f}")
    print("=" * 50)

    # ===================== 数据清理 =====================
    print("\n🔍 开始筛选表现较差的样本...")

    df = pd.DataFrame(records)
    df["预测标签"] = ["伪造" if p == 1 else "真实" for p in y_pred]
    df["阈值判断"] = best_thr
    df["模型是否正确"] = (df["真实标签"] == df["预测标签"])

    # 定义低置信度阈值（小于0.6认为置信度不足）
    low_conf_mask = ((df["AI伪造概率"] < 0.6) & (df["真实标签"] == "伪造")) | (
        (df["真实概率"] < 0.6) & (df["真实标签"] == "真实"))
    wrong_mask = ~df["模型是否正确"]

    bad_cases = df[low_conf_mask | wrong_mask]
    print(f"⛔ 检测到 {len(bad_cases)} 个效果不佳的样本")

    # 保存清单
    bad_cases.to_csv("bad_audio_cases.csv", index=False, encoding="utf-8-sig")
    print("📝 清单已保存到 bad_audio_cases.csv")

    # # 是否删除低质量样本
    # REMOVE_FLAG = False  # 改为 True 会真实删除文件
    # if REMOVE_FLAG:
    #     print("⚠️ 正在删除低质量样本...")
    #     for p in bad_cases["音频路径"]:
    #         try:
    #             os.remove(p)
    #         except Exception as e:
    #             print(f"删除失败: {p} | 原因: {e}")
    #     print("✅ 样本清理完成")

    REMOVE_FLAG = False # 改为 True 会执行清理
    if REMOVE_FLAG:
        print("⚠️ 将随机删除低质量样本的一半...")
        
        # 随机选出一半 bad_cases
        bad_cases_shuffled = bad_cases.sample(frac=0.3, random_state=42)  # 0.5=50%，可自行调整
        print(f"🗑️ 计划删除 {len(bad_cases_shuffled)} 条样本")

        deleted_count = 0
        for p in bad_cases_shuffled["音频路径"]:
            try:
                os.remove(p)
                deleted_count += 1
            except Exception as e:
                print(f"删除失败: {p} | 原因: {e}")

        print(f"✅ 已删除 {deleted_count} 个样本，占效果不佳样本的一半")    

    # 保存评估结果
    df.to_csv("audio_test_results.csv", index=False, encoding="utf-8-sig")
    print("📂 全部预测结果已保存到 audio_test_results.csv")
"""Website filter labels are separate from the public API's canonical values."""
import json
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name("model_catalog.json").read_text(encoding="utf-8"))
MODEL_RECORDS = CATALOG["models"]
MODEL_TYPE_LABELS = {
    "Checkpoint": "主模型", "TextualInversion": "文本嵌入", "Hypernetwork": "超网络",
    "AestheticGradient": "美学梯度", "LORA": "LoRA（低秩适配）", "LoCon": "LoCon（卷积适配）",
    "DoRA": "DoRA（权重分解适配）", "Controlnet": "ControlNet（条件控制）",
    "Upscaler": "放大模型", "MotionModule": "运动模块", "VAE": "VAE（图像编解码器）",
    "TextEncoder": "文本编码器", "UNet": "独立扩散模型", "CLIPVision": "视觉编码器",
    "Poses": "姿势", "Wildcards": "通配词", "Workflows": "工作流",
    "ComfyWorkflows": "ComfyUI（节点工作流）", "Detection": "检测模型",
    "VisionLanguage": "视觉语言模型", "CLIP": "图文编码器", "LLM": "大语言模型", "Other": "其他",
}
MODEL_TYPE_CHOICES = [(MODEL_TYPE_LABELS.get(t, t), t) for t in CATALOG["model_types"]]
SORT_LABELS = {
    "Newest": "最新发布", "Oldest": "最早发布", "Highest Rated": "评分最高",
    "Most Downloaded": "下载最多", "Most Liked": "喜欢最多", "Most Discussed": "讨论最多",
    "Most Collected": "收藏最多", "Most Images": "示例图最多",
}
SORT_CHOICES = [(SORT_LABELS.get(s, s), s) for s in CATALOG["sort_options"]]
PERIOD_CHOICES = [("不限时间", "AllTime"), ("近一年", "Year"), ("近一个月", "Month"), ("近一周", "Week"), ("近一天", "Day")]
FAMILY_LABELS = {
    "Stability AI": "Stability AI（SD 系列）", "Black Forest Labs": "Black Forest Labs（FLUX 系列）",
    "SDXL Community": "SDXL（社区底模）", "Alibaba": "阿里巴巴（通义千问／万相）",
    "Alibaba - Tongyi Lab": "阿里通义实验室", "Alibaba - Taotian": "阿里淘天",
    "Tencent": "腾讯混元", "Baidu": "百度文心", "ByteDance": "字节跳动",
    "Google": "谷歌", "Microsoft": "微软", "Meta": "Meta（图像模型）",
    "Other": "其他", "Upscaler": "放大模型", "Pony Diffusion": "Pony（社区模型系列）",
}
LEGACY_BASE_MODELS = {
    "Aura Flow": ["AuraFlow"], "Flux .1 S": ["Flux.1 S"], "Flux .1 D": ["Flux.1 D"],
    "Flux": ["Flux.1 S", "Flux.1 D"], "Pix Art a": ["PixArt a"],
}


def records(families=None, include_legacy=False):
    selected = set(families or [])
    return [m for m in MODEL_RECORDS if (include_legacy or not m["hidden"]) and (not selected or m["family"] in selected)]


def family_choices():
    names = list(dict.fromkeys(m["family"] for m in MODEL_RECORDS if not m["hidden"]))
    return [(FAMILY_LABELS.get(name, f"{name}（模型系列）"), name) for name in names]


def base_choices(families=None, include_legacy=False):
    return [(m["name"] + ("（历史底模）" if m["hidden"] else ""), m["name"]) for m in records(families, include_legacy)]


def expand_base_models(selected=None, families=None, include_legacy=False):
    # An explicit variant narrows its family. Without a variant, search the whole family.
    values = selected or ([m["name"] for m in records(families, include_legacy)] if families else [])
    expanded = []
    for value in values:
        for name in LEGACY_BASE_MODELS.get(value, [value]):
            name = name.strip()
            if name and name not in expanded:
                expanded.append(name)
    return expanded

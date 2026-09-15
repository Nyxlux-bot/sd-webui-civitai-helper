"""Chinese display labels; stored option values and API identifiers stay unchanged."""
LOCAL_TYPES = {
    "ckp": "主模型", "lora": "LoRA（低秩模型）", "lycoris": "LyCORIS（低秩适配）",
    "ti": "文本嵌入", "hyper": "超网络", "vae": "图像编解码器", "textencoder": "文本编码器",
    "controlnet": "条件控制模型", "detection": "检测模型", "upscaler": "放大模型",
}
FILES = {"Model":"模型文件", "Config":"配置文件", "VAE":"图像编解码器", "Diffusion Model":"扩散模型", "Text Encoder":"文本编码器"}
BUTTONS = {"replace_preview_button":"替换预览图", "open_url_button":"打开模型网页", "add_trigger_words_button":"添加触发词",
           "add_preview_prompt_button":"使用预览提示词", "rename_model_button":"重命名模型", "remove_model_button":"删除模型"}
RATINGS = {"PG":"全年龄", "PG13":"13 岁以上", "R":"限制级", "X":"成人", "XXX":"成人露骨内容", "Blocked":"包含网站屏蔽级别"}


def choices(values, labels):
    return [(labels.get(value, value), value) for value in values]

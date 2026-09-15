"""Civitai model browser with Chinese controls and current filter metadata."""
import html
import os
from html.parser import HTMLParser
from string import Template
from urllib.parse import urlsplit

import gradio as gr
from ch_lib import civitai, util
from .catalog import (MODEL_TYPE_CHOICES, MODEL_TYPE_LABELS, PERIOD_CHOICES, SORT_CHOICES,
                      base_choices, expand_base_models, family_choices)
from .search import make_params, search_page


def civitai_search():
    with gr.Blocks(analytics_enabled=False) as browser:
        make_ui()
    return browser


def make_ui():
    state = gr.State({})
    gr.Markdown("## 浏览与搜索模型")
    gr.Markdown("先按底模系列缩小范围，再选择具体训练底模。留空表示不限；可以同时选择多个系列和模型类型。")
    with gr.Row(equal_height=True):
        query = gr.Textbox(label="搜索关键词", placeholder="模型名称或关键词", lines=1, elem_id="ch_browser_query", scale=2)
        tag = gr.Textbox(label="模型标签", placeholder="标签名称，可留空", lines=1, elem_id="ch_browser_tag")
        username = gr.Textbox(label="作者", placeholder="网站用户名，可留空", lines=1, elem_id="ch_browser_author")
    with gr.Row(equal_height=True):
        families = gr.Dropdown(label="底模系列", choices=family_choices(), value=[], multiselect=True, elem_id="ch_browser_families")
        base_models = gr.Dropdown(label="训练底模", choices=base_choices(), value=[], multiselect=True,
                                  allow_custom_value=True, elem_id="ch_browser_bases",
                                  info="可输入网站新增底模的准确名称；未选具体底模时搜索所选系列的全部底模。")
        types = gr.Dropdown(label="模型类型", choices=MODEL_TYPE_CHOICES, value=[], multiselect=True, elem_id="ch_browser_types")
    with gr.Row(equal_height=True):
        period = gr.Dropdown(label="发布时间范围", choices=PERIOD_CHOICES, value="AllTime", elem_id="ch_browser_period")
        sort = gr.Dropdown(label="排序方式", choices=SORT_CHOICES, value="Newest", elem_id="ch_browser_sort")
        checkpoint = gr.Dropdown(label="主模型类别", choices=[("不限", ""), ("训练模型", "Trained"), ("融合模型", "Merge")], value="", elem_id="ch_browser_checkpoint")
        limit = gr.Dropdown(label="每页数量", choices=[20, 40, 60], value=20, elem_id="ch_browser_limit")
    with gr.Row():
        legacy = gr.Checkbox(label="显示历史底模", value=False, elem_id="ch_browser_legacy")
        allow_nsfw = gr.Checkbox(label="包含成人模型", value=False, elem_id="ch_browser_nsfw",
                                 info="预览图片仍遵守助手设置中的图片分级上限。")
        clear = gr.Button("清空筛选", elem_id="ch_browser_clear")
        search = gr.Button("搜索模型", variant="primary", elem_id="ch_browser_search")
    message = gr.Markdown("输入筛选条件后点击“搜索模型”。", elem_id="ch_browser_status")
    with gr.Row(equal_height=True):
        previous = gr.Button("上一页", interactive=False, elem_id="ch_browser_previous")
        following = gr.Button("下一页", interactive=False, elem_id="ch_browser_next")
    results = gr.HTML(value="", label="搜索结果", elem_id="ch_model_search_results")

    def choose_family(selected, old_bases, historical):
        choices = base_choices(selected, historical)
        allowed = {value for _, value in choices}
        value = [name for name in (old_bases or []) if name in allowed]
        return gr.update(choices=choices, value=value)

    families.change(choose_family, [families, base_models, legacy], base_models, queue=False)
    legacy.change(choose_family, [families, base_models, legacy], base_models, queue=False)

    def perform_search(old_state, q, t, author, age, ordering, groups, bases, model_types, historical,
                       checkpoint_type, page_limit, nsfw, evt: gr.EventData):
        direction = "previous" if evt.target == previous else "next" if evt.target == following else "search"
        params = {"query": q.strip(), "tag": t.strip(), "username": author.strip().lstrip("@"),
                  "period": age, "periodMode": "published", "sort": ordering, "types": model_types,
                  "baseModels": expand_base_models(bases, groups, historical),
                  "limit": int(page_limit), "nsfw": bool(nsfw)}
        if not model_types or "Checkpoint" in model_types:
            params["checkpointType"] = checkpoint_type
        try:
            api_key = util.get_opts("ch_civiai_api_key")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
            fetch = lambda url: civitai.civitai_get(url, headers=headers, max_retries=1, timeout=20)
            new_state, response, has_previous, has_next = search_page(old_state, params, direction, fetch, civitai.URLS["query"])
            content = parse_civitai_response(response)
            count = len(content["models"])
            cards = make_cards(content["models"])
            page_html = quick_template_from_file("container.html").safe_substitute(cards="".join(cards)) if count else '<div class="ch-browser-empty">没有找到符合条件的模型。可减少筛选条件后重试。</div>'
            status = f"第 {new_state['current_page'] + 1} 页 · 本页 {count} 个模型"
            return new_state, page_html, gr.update(interactive=has_previous), gr.update(interactive=has_next), status
        except Exception:
            # Keep history and results intact so the failed page can be retried.
            old_state = old_state or {}
            index = old_state.get("current_page", 0)
            return (old_state, gr.update(), gr.update(interactive=index > 0),
                    gr.update(interactive=index + 1 < len(old_state.get("pages", []))),
                    "搜索失败，请检查网络、访问凭据或筛选条件后重试。")

    inputs = [state, query, tag, username, period, sort, families, base_models, types, legacy, checkpoint, limit, allow_nsfw]
    outputs = [state, results, previous, following, message]
    for button in [search, previous, following]:
        button.click(perform_search, inputs, outputs)
    query.submit(perform_search, inputs, outputs)

    def clear_filters():
        return ({}, "", "", "", "AllTime", "Newest", [], gr.update(choices=base_choices(), value=[]), [],
                False, "", 20, False, "", gr.update(interactive=False), gr.update(interactive=False), "筛选条件已清空。")
    clear.click(clear_filters, outputs=inputs + [results, previous, following, message], queue=False)


def parse_model(model):
    model_id = int(model["id"])
    versions = {}
    bases = []
    preview = {"type": None, "url": None}
    threshold = civitai.NSFW_LEVELS.get(util.get_opts("ch_nsfw_threshold"), 1)
    for version in model.get("modelVersions") or []:
        base = version.get("baseModel")
        if base and base not in bases:
            bases.append(base)
        versions[version["id"]] = base
        for image in version.get("images") or []:
            if preview["url"] or image.get("type", "image") != "image":
                continue
            rating = image.get("nsfwLevel")
            if not isinstance(rating, (int, float)) or rating > threshold:
                continue
            url = safe_url(image.get("url"))
            if url:
                preview = {"type": "image", "url": url}
    return {"id": model_id, "name": model.get("name") or "未命名模型", "description": model.get("description") or "",
            "url": f"{civitai.URLS['modelPage']}{model_id}", "type": model.get("type", "Other"),
            "base_models": bases, "preview": preview, "versions": versions}


def parse_civitai_response(content):
    models = []
    for model in content.get("items") or []:
        try:
            models.append(parse_model(model))
        except (KeyError, TypeError, ValueError):
            continue
    return {"models": models, "meta": {"next_page": (content.get("metadata") or {}).get("nextPage")}}


def safe_url(value):
    if not isinstance(value, str):
        return ""
    try:
        url = urlsplit(value)
        return value if url.scheme in {"https", "http"} and url.hostname and not url.username and not url.password else ""
    except ValueError:
        return ""


class PlainDescription(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1
        elif tag in {"p", "div", "br", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def quick_template_from_file(filename):
    with open(os.path.join(util.script_dir, "browser/templates", filename), encoding="utf-8") as file:
        return Template(file.read())


def make_cards(models):
    card_template = quick_template_from_file("model_card.html")
    preview_template = quick_template_from_file("image_preview.html")
    cards = []
    for model in models:
        preview = '<span class="ch-browser-no-preview">暂无符合分级的预览</span>'
        if safe_url(model["preview"]["url"]):
            preview = preview_template.safe_substitute(preview_url=html.escape(model["preview"]["url"], quote=True))
        description = PlainDescription()
        description.feed(model["description"])
        cards.append(card_template.safe_substitute(
            model_id=int(model["id"]), name=html.escape(model["name"], quote=True), preview=preview,
            url=html.escape(safe_url(model["url"]), quote=True),
            base_models=html.escape(" / ".join(model["base_models"]) or "未标注底模"),
            type=html.escape(MODEL_TYPE_LABELS.get(model["type"], model["type"])),
            description=html.escape("".join(description.parts).strip() or "暂无说明"),
        ))
    return cards

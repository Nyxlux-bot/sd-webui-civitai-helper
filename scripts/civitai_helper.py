""" -*- coding: UTF-8 -*-
This extension can help you manage your models from civitai.
 It can download preview, add trigger words, open model page and use the prompt from preview image
repo: https://github.com/butaixianran/
"""

import os
import gradio as gr
import modules
from modules import scripts
from modules import shared
from modules import script_callbacks
from ch_lib import model
from ch_lib import js_action_civitai
from ch_lib import civitai
from ch_lib import util
from ch_lib import sections
from ch_lib import labels
from browser import browser

# init
# root path
ROOT_PATH = os.getcwd()

# extension path
EXTENSION_PATH = scripts.basedir()

util.script_dir = EXTENSION_PATH

# default hidden values for civitai helper buttons
BUTTONS = {
    "replace_preview_button": False,
    "open_url_button": False,
    "add_trigger_words_button": False,
    "add_preview_prompt_button": False,
    "rename_model_button": False,
    "remove_model_button": False,
}

model.get_custom_model_folder()

def update_proxy():
    """ Set proxy, allow for changes at runtime """
    proxy = util.get_opts("ch_proxy")

    util.printD(f"Set Proxy: {proxy}")
    if proxy:
        util.PROXIES["http"] = proxy
        util.PROXIES["https"] = proxy
        return

    util.PROXIES["http"] = None
    util.PROXIES["https"] = None


def on_ui_tabs():
    # init
    # init_py_msg = {
    #     # relative extension path
    #     "EXTENSION_PATH": util.get_relative_path(EXTENSION_PATH, ROOT_PATH),
    # }
    # init_py_msg_str = json.dumps(init_py_msg)

    # get prompt textarea
    # check modules/ui.py, search for txt2img_paste_fields
    # Negative prompt is the second element
    txt2img_prompt = modules.ui.txt2img_paste_fields[0][0]
    txt2img_neg_prompt = modules.ui.txt2img_paste_fields[1][0]
    img2img_prompt = modules.ui.img2img_paste_fields[0][0]
    img2img_neg_prompt = modules.ui.img2img_paste_fields[1][0]

    # Used by some elements to pass messages to python
    js_msg_txtbox = gr.Textbox(
        label='前端请求消息',
        visible=False,
        lines=1,
        value="",
        elem_id="ch_js_msg_txtbox"
    )

    # ====UI====
    with gr.Blocks(
        analytics_enabled=False
    ) as civitai_helper:
    # with gr.Blocks(css=".block.padded {padding: 10px !important}") as civitai_helper:

        # init
        with gr.Box(elem_classes="ch_box"):
            sections.scan_models_section()

        with gr.Box(elem_classes="ch_box"):
            sections.get_model_info_by_url_section()

        with gr.Box(elem_classes="ch_box"):
            gr.Markdown('### 下载模型')
            with gr.Tab('单个下载', elem_id="ch_dl_single_tab"):
                sections.download_section()
            with gr.Tab('批量下载'):
                sections.download_multiple_section()

        with gr.Box(elem_classes="ch_box"):
            sections.scan_for_duplicates_section()

        with gr.Box(elem_classes="ch_box"):
            sections.check_new_versions_section(js_msg_txtbox)

        # ====Footer====
        gr.HTML(f"<center>模型助手 · 中文维护版 {util.VERSION}</center>")

        # ====hidden component for js, not in any tab====
        js_msg_txtbox.render()
        py_msg_txtbox = gr.Textbox(
            label='后端响应消息',
            visible=False,
            lines=1,
            value="",
            elem_id="ch_py_msg_txtbox"
        )

        js_open_url_btn = gr.Button(
            value='打开模型网页',
            visible=False,
            elem_id="ch_js_open_url_btn"
        )
        js_add_trigger_words_btn = gr.Button(
            value='添加触发词',
            visible=False,
            elem_id="ch_js_add_trigger_words_btn"
        )
        js_use_preview_prompt_btn = gr.Button(
            value='使用预览图提示词',
            visible=False,
            elem_id="ch_js_use_preview_prompt_btn"
        )
        js_rename_card_btn = gr.Button(
            value='重命名模型',
            visible=False,
            elem_id="ch_js_rename_card_btn"
        )
        js_remove_card_btn = gr.Button(
            value='删除模型',
            visible=False,
            elem_id="ch_js_remove_card_btn"
        )

        # ====events====
        # js action
        js_open_url_btn.click(
            js_action_civitai.open_model_url,
            inputs=[js_msg_txtbox],
            outputs=py_msg_txtbox
        )
        js_add_trigger_words_btn.click(
            js_action_civitai.add_trigger_words,
            inputs=[js_msg_txtbox],
            outputs=[
                txt2img_prompt, img2img_prompt
            ]
        )
        js_use_preview_prompt_btn.click(
            js_action_civitai.use_preview_image_prompt,
            inputs=[js_msg_txtbox],
            outputs=[
                txt2img_prompt, txt2img_neg_prompt,
                img2img_prompt, img2img_neg_prompt
            ]
        )
        js_rename_card_btn.click(
            js_action_civitai.rename_model_by_path,
            inputs=[js_msg_txtbox],
            outputs=py_msg_txtbox
        )
        js_remove_card_btn.click(
            js_action_civitai.remove_model_by_path,
            inputs=[js_msg_txtbox],
            outputs=py_msg_txtbox
        )

    if util.get_opts("ch_civitai_browser"):
        civitai_helper_browser = browser.civitai_search()

        # the third parameter is the element id on html, with a "tab_" as prefix
        return (
            (civitai_helper, "模型助手", "civitai_helper"),
            (civitai_helper_browser, "模型浏览", "civitai_helper_browser")
        )

    return ((civitai_helper, "模型助手", "civitai_helper"),)


def on_ui_settings():
    section = ('civitai_helper', "模型助手")
    shared.opts.add_option(
        "ch_civiai_api_key",
        shared.OptionInfo(
            "",
            (
                'Civitai（模型网站）访问密钥；部分模型下载需要身份验证。可在使用说明中查看获取方法。'
            ),
            gr.Textbox,
            {"interactive": True, "max_lines": 1, "type": "password"},
            section=section
        ).link(
            "使用说明",
            "https://github.com/zixaphir/Stable-Diffusion-Webui-Civitai-Helper/wiki/Civitai-API-Key"
        )
    )
    shared.opts.add_option(
        "ch_autov3",
        shared.OptionInfo(
            False,
            (
                '扫描时使用 autoV3（跳过文件头的哈希算法），便于识别被其他工具修改过元数据的模型。'
            ),
            gr.Checkbox,
            {"interactive": True},
            section=section)
    )
    shared.opts.add_option(
        "ch_dl_lyco_to_lora",
        shared.OptionInfo(
            False,
            (
                '将 LyCORIS（低秩适配模型）保存到低秩模型目录；使用旧版绘图界面或独立适配插件时请保持关闭。'
            ),
            gr.Checkbox,
            {"interactive": True},
            section=section)
    )
    shared.opts.add_option(
        "ch_open_url_with_js",
        shared.OptionInfo(
            True,
            (
                '在当前浏览器打开模型网页；关闭后由运行绘图服务的电脑打开。'
            ),
            gr.Checkbox,
            {"interactive": True},
            section=section
        )
    )
    shared.opts.add_option(
        "ch_hide_buttons",
        shared.OptionInfo(
           [x for x, y in BUTTONS.items() if y],
           '隐藏勾选的模型卡片操作',
           gr.CheckboxGroup,
           {"choices": labels.choices(BUTTONS, labels.BUTTONS)},
           section=section
        )
   )
    shared.opts.add_option(
        "ch_always_display",
        shared.OptionInfo(
            False,
            '始终显示模型卡片操作按钮',
            gr.Checkbox,
            {"interactive": True},
            section=section
        )
    )
    shared.opts.add_option(
        "ch_max_size_preview",
        shared.OptionInfo(
            True,
            '下载原尺寸预览图',
            gr.Checkbox,
            {"interactive": True},
            section=section
        )
    )
    shared.opts.add_option(
        "ch_download_examples",
        shared.OptionInfo(
            False,
            '将示例图下载到本地',
            gr.Checkbox,
            {"interactive": True},
            section=section
        )
    )
    shared.opts.add_option(
        "ch_nsfw_threshold",
        shared.OptionInfo(
            list(civitai.NSFW_LEVELS.keys())[0], # Block NSFW
            "预览图片的最高分级；超过所选级别的图片不会展示或下载。",
            gr.Dropdown,
            {
                "choices": labels.choices(civitai.NSFW_LEVELS, labels.RATINGS),
                "interactive": True
            },
            section=section
        )
    )
    shared.opts.add_option(
        "ch_preview_nsfw_selection_behavior",
        shared.OptionInfo(
            "API Order (default)",
            '符合图片分级上限时的预览选择顺序',
            gr.Dropdown,
            {
                "choices": [("网站默认顺序", "API Order (default)"), ("优先较低分级", "Lowest Rating First")],
                "interactive": True
            },
            section=section
        )
    )
    shared.opts.add_option(
        "ch_dl_webui_metadata",
        shared.OptionInfo(
            True,
            '同时补充绘图界面的模型元数据',
            gr.Checkbox,
            {"interactive": True},
            section=section)
    )
    shared.opts.add_option(
        "ch_proxy",
        shared.OptionInfo(
            "",
            '网络代理地址；填写完整的代理协议、主机和端口。留空使用默认网络。',
            gr.Textbox,
            {"interactive": True, "max_lines": 1},
            section=section)
    )
    shared.opts.add_option(
        "ch_clean_html",
        shared.OptionInfo(
            False,
            '清除模型说明中的网页格式',
            gr.Checkbox,
            {"interactive": True},
            section=section)
    )
    shared.opts.add_option(
        "ch_civitai_browser",
        shared.OptionInfo(
            True,
            '启用模型浏览与搜索页面',
            gr.Checkbox,
            {"interactive": True},
            section=section)
    )
    shared.opts.add_option(
        "ch_image_metadata",
        shared.OptionInfo(
            False,
            '自动向生成图片写入模型资源信息，便于网站识别所用模型。详见使用说明。',
            gr.Checkbox,
            {"interactive": True},
            section=section
        ).link(
            "使用说明",
            "https://github.com/zixaphir/Stable-Diffusion-Webui-Civitai-Helper/wiki/Civitai-Resource-Metadata"
        )
    )
    shared.opts.add_option(
        "ch_set_file_timestamp",
        shared.OptionInfo(
            False,
            '将下载文件的时间设为模型创建时间',
            gr.Checkbox,
            {"interactive": True},
            section=section)
    )
    shared.opts.onchange(
        "ch_proxy",
        update_proxy
    )

util.GRADIO_FALLBACK = not util.newer_version(gr.__version__, "4.0.0")

script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_ui_tabs(on_ui_tabs)

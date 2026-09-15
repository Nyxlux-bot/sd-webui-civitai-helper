""" -*- coding: UTF-8 -*-
Sections for civitai_helper tab.
"""

import gradio as gr
import re
from . import model
from . import js_action_civitai
from . import model_action_civitai
from . import civitai
from . import duplicate_check
from . import util
from . import labels

model_types = list(model.folders.keys())
model_type_choices = labels.choices(model_types, labels.LOCAL_TYPES)

def scan_models_section():
    """ Scan Models Section """
    with gr.Row():
        gr.Markdown('### 扫描并补全模型信息')
    with gr.Row():
        with gr.Column():
            scan_model_types_drop = gr.CheckboxGroup(
                choices=model_type_choices,
                label='模型类型',
                value=model_types
            )
    with gr.Row():
        with gr.Column():
            organize_models = gr.Checkbox(
                label='按模型类别整理到子目录',
                value=False,
                elem_id="organize_models"
            )
            refetch_old_ckb = gr.Checkbox(
                label='替换旧版元数据格式',
                value=False,
                elem_id="ch_refetch_old_ckb"
            )
            gr.HTML('<p>替换旧格式可能覆盖手动编辑的元数据，使用前请备份。<a href="https://github.com/zixaphir/Stable-Diffusion-Webui-Civitai-Helper/wiki/Metadata-Format-Changes">格式变更说明</a></p>')

        with gr.Column():
            scan_model_civitai_btn = gr.Button(
                value='开始扫描',
                variant="primary",
                elem_id="ch_scan_model_civitai_btn"
            )

            # scan_civitai_info_image_meta_btn = gr.Button(
            #     value="Update image generation information (Experimental)",
            #     variant="primary",
            #     elem_id="ch_Scan_civitai_info_image_meta_btn"
            # )

    with gr.Row():
        scan_model_log_md = gr.Markdown(
            value='点击扫描后将在此显示进度；详细信息可在运行窗口查看。',
            elem_id="ch_scan_model_log_md"
        )

    # ====events====
    scan_model_civitai_btn.click(
        model_action_civitai.scan_model,
        inputs=[
            scan_model_types_drop,
            refetch_old_ckb,
            organize_models
        ],
        outputs=scan_model_log_md
    )

    # scan_civitai_info_image_meta_btn.click(
    #     model.scan_civitai_info_image_meta,
    #     outputs=scan_model_log_md
    # )

def get_model_info_by_url_section():
    """ Get Civitai Model Info by Model Page URL Section """

    def get_model_names_by_input(model_type, empty_info_only):
        names = civitai.get_model_names_by_input(model_type, empty_info_only)
        if util.GRADIO_FALLBACK:
            return model_name_drop.update(choices=names, value="")
        return gr.Dropdown(choices=names, value="")

    no_info_model_names = civitai.get_model_names_by_input("ckp", False)

    with gr.Column():
        gr.Markdown('### 通过链接关联模型')
        gr.Markdown('自动扫描无法识别本地模型时，可通过模型链接手动关联。')
        with gr.Row():
            with gr.Column(scale=2):
                model_type_drop = gr.Dropdown(
                    choices=model_type_choices,
                    label='模型类型',
                    value="ckp",
                    multiselect=False,
                    elem_classes="ch_vpadding"
                )
            with gr.Column(scale=1):
                empty_info_only_ckb = gr.Checkbox(
                    label='只显示缺少信息的模型',
                    value=False,
                    elem_id="ch_empty_info_only_ckb",
                    elem_classes="ch_vpadding"
                )
        with gr.Row():
            with gr.Column(scale=2):
                model_name_drop = gr.Dropdown(
                    choices=no_info_model_names,
                    label='模型',
                    value="",
                    multiselect=False
                )
        with gr.Row():
            with gr.Column(scale=2, elem_classes="justify-bottom"):
                model_url_or_id_txtbox = gr.Textbox(
                    label='模型链接或编号',
                    lines=1,
                    value=""
                )
            with gr.Column(scale=1, elem_classes="justify-bottom"):
                get_civitai_model_info_by_id_btn = gr.Button(
                    value='获取模型信息',
                    variant="primary"
                )

    get_model_by_id_log_md = gr.Markdown("")

    # ====events====
    model_type_drop.change(
        get_model_names_by_input,
        inputs=[
            model_type_drop, empty_info_only_ckb
        ],
        outputs=model_name_drop
    )
    empty_info_only_ckb.change(
        get_model_names_by_input,
        inputs=[
            model_type_drop, empty_info_only_ckb
        ],
        outputs=model_name_drop
    )

    get_civitai_model_info_by_id_btn.click(
        model_action_civitai.get_model_info_by_input,
        inputs=[
            model_type_drop, model_name_drop,
            model_url_or_id_txtbox
        ],
        outputs=get_model_by_id_log_md
    )

def filter_previews(previews):
    images = []
    nsfw_preview_threshold = util.get_opts("ch_nsfw_threshold")
    selection_behavior = util.get_opts("ch_preview_nsfw_selection_behavior") or "API Order (default)"
    for preview in previews:
        try:
            nsfw_level = preview["nsfwLevel"]
        except KeyError:
            util.printD("NSFW status of preview image could not be determined. :(")
            if nsfw_preview_threshold != civitai.NSFW_LEVELS["XXX"]:
                continue
            nsfw_level = 0

        if civitai.NSFW_LEVELS[nsfw_preview_threshold] < nsfw_level:
            continue
        if preview["type"] == "image":
            # Civitai added videos as previews, and webui does not like it
            images.append((nsfw_level, preview["url"]))

    if selection_behavior == "Lowest Rating First":
        images.sort(key=lambda x: x[0])

    return [url for _, url in images]

def download_section():
    """ Download Models Section """

    model_filetypes = civitai.FILE_TYPES
    file_elems = {}

    dl_state = gr.State({
        "model_info": {},
        "filenames": {
            # dl_version_str: filename,
        },
        "base_models": {
            # dl_version_str: base_model,
        },
        "previews": {
            # dl_version_str: [{url: url, nsfw: nsfw}],
        },
        "files": {
            # dl_version_str: {
            #   Model: bool,
            #   Config: bool,
            #   ...
            # }
        },
        "files_count": {
            # dl_version_str: int
        },
        "filtered_previews": []
    })

    def get_model_info_by_url(url, subfolder):
        result = civitai.get_model_id_from_url(url, include_model_ver=True)
        if not result:
            raise gr.Error("请输入有效的模型链接或编号。")
        model_id, model_version_id = result
        data = model_action_civitai.get_model_info_by_id(model_id)

        if not data:
            raise gr.Error("无法获取可下载的模型版本。请检查链接、访问凭据，或在模型网页确认此模型类型是否可用于当前绘图界面。")

        state = {
            "model_info": {},
            "filenames": {},
            "base_models": {},
            "previews": {},
            "files": {},
            "files_count": {},
            "filtered_previews": []
        }

        state["model_info"] = data["model_info"]
        state["previews"] = data["previews"]

        subfolders = sorted(data["subfolders"])
        version_strs = data["version_strs"]
        base_models = data["base_models"]
        filenames = data["filenames"]

        if subfolder == "" or subfolder not in subfolders:
            # Try to auto-select a subfolder from the first matched model's tags
            tags = data["model_info"].get("tags", [])
            subfolder = "/"
            for tag in tags:
                cleaned_tag = re.sub(r"[^a-z0-9\s]+", "", str(tag).lower()).strip()
                cleaned_tag = re.sub(r"\s+", " ", cleaned_tag)
                for sf in subfolders:
                    if cleaned_tag in sf.lower():
                        subfolder = sf
                        break
                if subfolder != "/":
                    break

        for filename, base_model, version in zip(filenames, base_models, version_strs):
            state["filenames"][version] = filename
            state["base_models"][version] = base_model

        for version_files, version in zip(data["files"], version_strs):
            filetypes = state["files"][version] = {}
            files_count = 0
            unhandled_files = []
            for filedata in version_files:
                files_count += 1
                ch_filedata = {
                    "id": filedata["id"],
                    "name": filedata["name"],
                }

                if filedata["type"] in model_filetypes:
                    filetypes[filedata["type"]] = (True, ch_filedata)
                    continue

                unhandled_files.append(f"{ch_filedata['id']}: {ch_filedata['name']}")

            if len(unhandled_files) > 0:
                filetypes["unhandled_files"] = "\n".join(unhandled_files)
            else:
                filetypes["unhandled_files"] = None

            state["files_count"][version] = files_count

        # Pre-select the version matching the modelVersionId query param, if present.
        default_version = version_strs[0]
        if model_version_id:
            for vs in version_strs:
                if vs.endswith(f"_{model_version_id}"):
                    default_version = vs
                    break

        if util.GRADIO_FALLBACK:
            return [
                state, data["model_name"], data["model_type"],
                dl_subfolder_drop.update(
                    choices=subfolders,
                    value=subfolder
                ),
                dl_version_drop.update(
                    choices=version_strs,
                    value=default_version
                ),
                files_row.update(
                    visible=True
                )
            ]

        return [
            state, data["model_name"], data["model_type"],
            gr.Dropdown(
                choices=subfolders,
                value=subfolder
            ),
            gr.Dropdown(
                choices=version_strs,
                value=default_version
            ),
            gr.Column(
                visible=True
            )
        ]

    def update_dl_inputs(state, dl_version, dl_preview_index):
        filename = state["filenames"][dl_version]

        if not filename:
            filename = dl_filename_txtbox.value

        base_model = state["base_models"][dl_version]

        file_parts = filename.split(".")
        ext = file_parts.pop()
        base = ".".join(file_parts)

        previews = filter_previews(state["previews"][dl_version])
        state["filtered_previews"] = previews

        preview = None
        if len(previews) > dl_preview_index:
            preview = previews[dl_preview_index]
        elif len(previews) > 0:
            preview = previews[0]

        output_add = []

        for key, elems in file_elems.items():
            filedata = state["files"][dl_version].get(key, False)

            visible = False
            filename = ""
            if filedata:
                visible = True
                if isinstance(filedata, str):
                    filename = ", ".join([
                        filedata_str.split(":")[1].strip()
                        for filedata_str in filedata.split("\n")
                    ])
                elif isinstance(filedata, tuple):
                    _, data = filedata
                    filename = data["name"]
                else:
                    raise ValueError(f"Invalid filedata: {filedata}")
            if util.GRADIO_FALLBACK:
                output_add.append(elems["txtbx"].update(value=filename))
                output_add.append(elems["row"].update(visible=visible))
            else:
                output_add.append(gr.Textbox(value=filename))
                output_add.append(gr.Row(visible=visible))

        if util.GRADIO_FALLBACK:
            return [
                state,
                dl_filename_txtbox.update(
                    value=base
                ),
                dl_extension_txtbox.update(
                    value=ext
                ),
                dl_preview_img.update(
                    value=previews
                ),
                dl_preview_url.update(
                    value=preview
                ),
                download_all_row.update(
                    visible=(state["files_count"][dl_version] > 1)
                ),
                dl_base_model_txtbox.update(
                    value=base_model
                )
            ] + output_add

        return [
            state,
            gr.Textbox(
                value=base
            ),
            gr.Textbox(
                value=ext
            ),
            gr.Gallery(
                value=previews
            ),
            gr.Textbox(
                value=preview
            ),
            gr.Row(
                visible=(state["files_count"][dl_version] > 1)
            ),
            gr.Textbox(
                value=base_model
            )
        ] + output_add

    def update_dl_files_visibility(dl_all):
        files_chkboxes = []
        for chkbox in ch_dl_model_types_visibility:
            if util.GRADIO_FALLBACK:
                files_chkboxes.append(
                    chkbox.update(
                        visible=not dl_all
                    )
                )
            else:
                files_chkboxes.append(
                    gr.Column(visible=not dl_all)
                )

        return files_chkboxes

    def update_dl_preview_url(state, dl_preview_index):
        preview_url = state["filtered_previews"][dl_preview_index]

        if util.GRADIO_FALLBACK:
            return dl_preview_url.update(
                value=preview_url
            )

        return gr.Textbox(
            value=preview_url
        )

    def update_dl_preview_index(evt: gr.SelectData):
        # For some reason, you can't pass gr.SelectData and
        # inputs at the same time. :/

        if util.GRADIO_FALLBACK:
            return dl_preview_index.update(
                value=evt.index
            )

        return gr.Number(
            value=evt.index
        )

    with gr.Row():
        with gr.Column(scale=2, elem_id="ch_dl_model_inputs"):

            gr.Markdown(value='**1. 输入链接并获取模型信息**')

            with gr.Row():
                with gr.Column(scale=2, elem_classes="justify-bottom"):
                    dl_model_url_or_id_txtbox = gr.Textbox(
                        label='模型链接或编号',
                        lines=1,
                        max_lines=1,
                        value="",
                        placeholder='输入模型链接或编号',
                        elem_id="ch_dl_url"
                    )
                with gr.Column(elem_classes="justify-bottom"):
                    dl_model_info_btn = gr.Button(
                        value='获取模型信息',
                        variant="primary",
                        elem_id="ch_dl_get_info"
                    )

            gr.Markdown(value='**2. 选择保存位置与模型版本**')

            with gr.Row(elem_classes="ch_grid"):
                dl_model_name_txtbox = gr.Textbox(
                    label='模型名称',
                    interactive=False,
                    lines=1,
                    max_lines=1,
                    min_width=320,
                    value=""
                )
                dl_model_type_txtbox = gr.Dropdown(
                    choices=model_type_choices,
                    label='模型类型',
                    interactive=False,
                    min_width=320,
                    value=None,
                )
                dl_base_model_txtbox = gr.Textbox(
                    label='训练底模',
                    interactive=False,
                    lines=1,
                    max_lines=1,
                    min_width=320,
                    value=""
                )
                dl_version_drop = gr.Dropdown(
                    choices=[],
                    label='模型版本',
                    value="",
                    min_width=320,
                    multiselect=False
                )
                dl_subfolder_drop = gr.Dropdown(
                    choices=[],
                    label='保存子目录',
                    value="",
                    min_width=320,
                    allow_custom_value=True,
                    multiselect=False
                )
                dl_duplicate_drop = gr.Dropdown(
                    choices=[("跳过", "Skip"), ("覆盖", "Overwrite"), ("为新文件重命名", "Rename New")],
                    label='遇到同名文件时',
                    value="Skip",
                    min_width=320,
                    multiselect=False
                )

            with gr.Column(
                visible=False,
                variant="panel"
            ) as files_row:

                with gr.Row(variant="compact"):
                    gr.Markdown('**下载文件**')

                ch_output_add = []
                ch_dl_model_types = []
                ch_dl_model_types_visibility = []

                for filetype in model_filetypes:
                    with gr.Row(
                        visible=False,
                        equal_height=True,
                    ) as row:
                        file_elems[filetype] = elems = {}
                        elems["row"] = row

                        with gr.Column(scale=0, min_width=24, elem_classes="flex-center") as ckb_column:
                            elems["ckb"] = filetype_ckb = gr.Checkbox(
                                label="",
                                value=True,
                                min_width=0,
                                interactive=("Model" not in filetype)
                            )
                        with gr.Column(scale=1, min_width=0):
                            elems["txtbx"] = gr.Textbox(
                                value="",
                                interactive=False,
                                label=labels.FILES.get(filetype, filetype),
                                max_lines=1,
                                min_width=0
                            )

                        ch_dl_model_types_visibility.append(ckb_column)
                        ch_dl_model_types.append(filetype_ckb)

                        ch_output_add.append(elems["txtbx"])
                        ch_output_add.append(row)

                with gr.Row(visible=False) as unhandled_files_row:
                    file_elems["unhandled_files"] = elems = {}
                    elems["row"] = row

                    elems["txtbx"] = gr.Textbox(
                        value="",
                        interactive=False,
                        label='其他附属文件（勾选“下载全部文件”时一并保存）',
                    )

                    ch_output_add.append(elems["txtbx"])
                    ch_output_add.append(unhandled_files_row)

                with gr.Row(visible=False) as download_all_row:
                    dl_all_ckb = gr.Checkbox(
                        label='下载全部文件',
                        value=False,
                        elem_id="ch_dl_all_ckb",
                        elem_classes="ch_vpadding"
                    )

        with gr.Column(scale=1, elem_id="ch_preview_col", min_width=512):
            with gr.Row(elem_classes="flex-center"):
                dl_preview_img = gr.Gallery(
                    show_label=True,
                    label='预览图',
                    value=None,
                    elem_id="ch_dl_preview_img",
                    allow_preview=True,
                    preview=False,
                    object_fit="scale-down"
                )
                dl_preview_url = gr.Textbox(
                    value="",
                    visible=False,
                    elem_id="ch_dl_preview_url"
                )
                dl_preview_index = gr.Number(
                    value=0,
                    visible=False,
                    elem_id="ch_dl_preview_index",
                    precision=0
                )

    with gr.Row():
        with gr.Column(scale=2, elem_classes="justify-bottom"):
            dl_filename_txtbox = gr.Textbox(
                label='保存文件名',
                value="",
                lines=1,
                max_lines=1,
                elem_id="ch_dl_filename_txtbox",
                elem_classes="ch_vpadding"
            )
            dl_extension_txtbox = gr.Textbox(
                label='模型扩展名',
                value="",
                elem_id="ch_dl_extension_txtbox",
                visible=False
            )

        with gr.Column(elem_classes="justify-bottom"):
            dl_civitai_model_by_id_btn = gr.Button(
                value='3. 下载模型',
                elem_classes="ch_vmargin",
                variant="primary",
                elem_id="ch_download_model_button"
            )

    with gr.Row():
        dl_log_md = gr.Markdown(
            value='选择模型版本后开始下载，进度会显示在这里。'
        )

    # ====events====
    dl_model_info_btn.click(
        get_model_info_by_url,
        inputs=[
            dl_model_url_or_id_txtbox, dl_subfolder_drop
        ],
        outputs=[
            dl_state, dl_model_name_txtbox,
            dl_model_type_txtbox, dl_subfolder_drop,
            dl_version_drop, files_row
        ]
    )

    dl_inputs = [
            dl_state, dl_model_type_txtbox,
            dl_subfolder_drop, dl_version_drop,
            dl_filename_txtbox, dl_extension_txtbox,
            dl_all_ckb,
            dl_duplicate_drop, dl_preview_url
        ] + ch_dl_model_types

    dl_civitai_model_by_id_btn.click(
        model_action_civitai.dl_model_by_input,
        inputs=dl_inputs,
        outputs=dl_log_md
    )

    ver_outputs = [
        dl_state, dl_filename_txtbox, dl_extension_txtbox,
        dl_preview_img, dl_preview_url, download_all_row, dl_base_model_txtbox,
    ] + ch_output_add

    dl_version_drop.change(
        update_dl_inputs,
        inputs=[dl_state, dl_version_drop, dl_preview_index],
        outputs=ver_outputs
    )
    dl_all_ckb.change(
        update_dl_files_visibility,
        inputs=dl_all_ckb,
        outputs=ch_dl_model_types_visibility
    )
    # Gradio has so many issues with Gradio.Gallery...
    dl_preview_img.select(
        update_dl_preview_index,
        None,
        dl_preview_index
    )
    dl_preview_index.change(
        update_dl_preview_url,
        [dl_state, dl_preview_index],
        dl_preview_url
    )

def download_multiple_section():
    """ Batch Model Download:
        Allows pasting multiple model links to download
    """

    download_options = {
        # Download all files, including unsupported files.
        # Supported files are controlled via `civitai.FILE_TYPES`
        "all_files": {
            "param": "AllFiles"
        },
        # Download every version of a model.
        "all_versions": {
            "param": "AllVersions"
        },
        "subdirectory": {
            "param": "Subfolder"
        }
    }

    def add_to_batch(url, subfolder, all_files, all_versions, urls):
        url_with_params = f"{url}"
        if all_files:
            url_with_params += "::AllFiles"
        if all_versions:
            url_with_params += "::AllVersions"
        if subfolder and subfolder not in ["", "/"]:
            url_with_params += f"::Subfolder={str(subfolder)}"

        if not urls or urls == "":
            appended_urls = url_with_params
        else:
            urls = f"{urls}".split("\n")
            urls.append(url_with_params)
            appended_urls = "\n".join(urls)

        if util.GRADIO_FALLBACK:
            return urls_txtbox.update(
                value=appended_urls
            )

        return gr.Textbox(
            lines=5,
            max_lines=100,
            placeholder='支持模型页面链接和模型版本链接。',
            label='待下载的模型',
            show_label=True,
            value=appended_urls
        )


    def detect_model_type(url, subfolder):
        model_id = civitai.get_model_id_from_url(url)
        data = model_action_civitai.get_model_info_by_id(model_id)

        if not data:
            print("Failed to get model info by url")
            return None

        state = {
            "model_info": {},
        }

        state["model_info"] = data["model_info"]

        subfolders = sorted(data["subfolders"])

        # remove leading slashes and double-slashes from subfolders
        subfolders = [directory.lstrip("\\").lstrip("/") for directory in subfolders]

        tags = data["model_info"].get("tags", [])
        for tag in tags:
            cleaned_tag = re.sub(r"[^a-z0-9\s]+", "", str(tag).lower()).strip()
            cleaned_tag = re.sub(r"\s+", " ", cleaned_tag)
            for sf in subfolders:
                if cleaned_tag in sf.lower():
                    subfolder = sf
                    break
            if subfolder != "":
                break

        if util.GRADIO_FALLBACK:
            return [
                dl_subfolder_drop.update(
                    choices=subfolders,
                    value=subfolder
                )
            ]

        return gr.Dropdown(
            choices=subfolders,
            label='保存子目录',
            value=subfolder,
            min_width=320,
            multiselect=False
        )


    def append_model_version_info(dl, model_version):
        """
        Adds the required information to download a particular model version
        givent the model and version's information.
        """
        dl["version_str"] = f"{model_version['name']}_{model_version['id']}"

        filetypes = []
        for file in model_version["files"]:
            if "Model" in file["type"]:
                filetypes.append("Model")
                filename = file["name"]
                filename_frags = filename.split(".")
                dl["file_ext"] = filename_frags.pop()
                dl["filename"] = ".".join(filename_frags)

            if file["type"] in civitai.FILE_TYPES:
                filetypes.append(file["type"])

        dl["filetypes"] = filetypes

        return dl

    def parse_params(params):
        """
        Parses a user-provided string to change file downloading options.
        """

        options = {}

        for key, option in download_options.items():
            options[key] = False
            for param in params:
                val = None
                param = param.strip()
                if "=" in param:
                    param, val = param.split("=")

                param = param.lower()
                if param == option["param"].lower():
                    if val:
                        options[key] = val
                        continue

                    options[key] = True

        return options

    def download_all_action(entries_txt:str):
        entries_txt = entries_txt.strip()
        entries = entries_txt.split("\n")
        dls = []

        nsfw_preview_threshold = util.get_opts("ch_nsfw_threshold")

        for entry in entries:
            url = None
            params = None
            options = None

            if "::" in entry:
                params = entry.split("::")
                url = params.pop(0)
            else:
                params = []
                url = entry

            options = parse_params(params)

            result = civitai.get_model_id_from_url(url, include_model_ver=True)

            if not result:
                continue

            model_id, model_version_id = result
            model_info = civitai.get_model_info_by_id(model_id)

            if not model_info:
                continue

            dl = {
                "model_name": model_info["name"],
                "model_info": model_info,
                "model_type": civitai.MODEL_TYPES[model_info["type"]],
                "subfolder": f"/{options['subdirectory'] or ''}",
                "version_str": None,
                "filename": None,
                "file_ext": None,
                "dl_all": options["all_files"],
                "nsfw_preview_threshold": nsfw_preview_threshold,
                "duplicate": "skip",
                "preview": None,
                "filetypes": None
            }

            model_version = None

            if options["all_versions"]:
                for model_version in model_info["modelVersions"]:
                    dl_version = append_model_version_info(dl.copy(), model_version)
                    dls.append(dl_version)

                continue

            try:
                if model_version_id:
                    for version in model_info["modelVersions"]:
                        if f"{version['id']}" == model_version_id:
                            model_version = version
                            break

            except KeyError:
                util.printD(f"Failed to find a model version for model {model_id}")
                continue

            if not model_version:
                model_version = model_info["modelVersions"][0]

            dl = append_model_version_info(dl, model_version)
            if not dl:
                continue

            dls.append(dl)

        i = 0
        count = len(dls)
        download_results = []
        for dl in dls:
            i = i + 1
            progress = None
            try:
                dl_status = "\n".join(download_results)
                status_msg = f"```\nCompleted:\n{dl_status}\n```"
                for progress in model_action_civitai.dl_model_by_input(
                    {"model_info": dl["model_info"]},
                    dl["model_type"],
                    dl["subfolder"],
                    dl["version_str"],
                    dl["filename"],
                    dl["file_ext"],
                    dl["dl_all"],
                    dl["duplicate"],
                    dl["preview"],
                    *dl["filetypes"]
                ):
                    yield f"{dl['model_name']} {i}/{count} {progress} \n {status_msg}"

                download_results.append(f"{dl['model_name']}: {progress}")
            except Exception as e:
                msg = None
                if hasattr(e, 'message'):
                    msg = e.message
                else:
                    msg = e

                output = f"下载过程中发生错误：{msg}\n{e.args}"
                util.printD(output)
                download_results.append(f" * {dl['model_name']}: {output}")

        download_results = "\n".join(download_results)
        yield f"```\n已完成：\n{download_results}\n```"
        return

    with gr.Row():
        gr.Markdown('每行输入一个模型链接，也可通过下方表单添加。链接后可用双冒号附加参数：\n\n- `AllFiles`（全部文件）\n- `AllVersions`（全部版本）\n- `Subfolder=style`（保存到已存在的子目录）\n\n参数不区分大小写。')
    with gr.Accordion('添加到批量下载'):
        with gr.Row():
            gr.Markdown('### 添加批量任务')
        with gr.Row():
            with gr.Column(scale=2, elem_classes="justify-bottom"):
                dl_model_url_or_id_txtbox = gr.Textbox(
                    label='模型链接或编号',
                    lines=1,
                    max_lines=1,
                    value="",
                    placeholder='模型页面链接',
                    elem_id="ch_dl_url"
                )
            with gr.Column(elem_classes="justify-bottom"):
                detect_model_type_btn = gr.Button(
                    value='识别模型类型',
                    variant="primary",
                    elem_id="ch_detect_model_type"
                )
        with gr.Row():
            with gr.Column():
                all_files = gr.Checkbox(label='包含全部文件', value=False)
            with gr.Column():
                all_versions = gr.Checkbox(label='包含全部版本', value=False)
        with gr.Row():
            dl_subfolder_drop = gr.Dropdown(
                    choices=[],
                    label='保存子目录',
                    value="",
                    min_width=320,
                    multiselect=False
                )
        with gr.Row():
            add_to_batch_btn = gr.Button(value='加入批量列表', variant="primary")
    with gr.Row():
        urls_txtbox = gr.Textbox(
            lines=5,
            max_lines=100,
            placeholder='支持模型页面链接和模型版本链接。',
            label='待下载的模型',
            show_label=True
        )

    with gr.Row():
        submit_btn = gr.Button(value='开始批量下载', variant="primary")

    with gr.Row():
        dl_all_log_md = gr.Markdown(
            value='详细进度可在绘图服务的运行窗口查看。'
        )

    detect_model_type_btn.click(
        detect_model_type,
        inputs=[
            dl_model_url_or_id_txtbox, dl_subfolder_drop
        ],
        outputs=dl_subfolder_drop
    )

    add_to_batch_btn.click(
        add_to_batch,
        inputs=[
            dl_model_url_or_id_txtbox, dl_subfolder_drop, all_files, all_versions, urls_txtbox
        ],
        outputs=urls_txtbox
    )

    submit_btn.click(
        download_all_action,
        inputs=urls_txtbox,
        outputs=dl_all_log_md
    )


def scan_for_duplicates_section():
    """ Scan Duplicate Models Section """
    with gr.Column():
        gr.Markdown('### 查找重复模型')
        with gr.Row():
            with gr.Column():
                scan_dup_model_types_drop = gr.CheckboxGroup(
                    choices=model_type_choices,
                    label='模型类型',
                    value=model_types
                )
        with gr.Row():
            with gr.Column(scale=2):
                cached_hash_ckb = gr.Checkbox(
                    label='使用元数据中的哈希值（便于识别裁剪模型，但可能误判）',
                    value=False,
                    elem_id="ch_cached_hash_ckb"
                )
            with gr.Column():
                scan_dup_model_btn = gr.Button(
                    value='开始扫描',
                    variant="primary",
                    elem_id="ch_scan_dup_model_civitai_btn"
                )

        # with gr.Row():
        scan_dup_model_log_md = gr.HTML(
            value='点击扫描后将在此显示进度；详细信息可在运行窗口查看。',
            elem_id="ch_scan_dup_model_log_md"
        )

    # ====events====
    scan_dup_model_btn.click(
        duplicate_check.scan_for_dups,
        inputs=[
            scan_dup_model_types_drop,
            cached_hash_ckb
        ],
        outputs=scan_dup_model_log_md
    )

def check_new_versions_section(js_msg_txtbox):
    """ Check models' new version section """

    with gr.Column():
        gr.Markdown('### 检查模型更新')
        with gr.Row():
            with gr.Column(scale=2):
                model_types_ckbg = gr.CheckboxGroup(
                    choices=model_type_choices,
                    label='模型类型',
                    value=[
                        "ti", "hyper", "ckp", "lora", "lycoris"
                    ]
                )
        with gr.Row():
            with gr.Column(scale=2):
                check_models_new_version_btn = gr.Button(
                    value='检查新版本',
                    variant="primary"
                )

        with gr.Row():
            with gr.Column():
                dl_new_version_log_md = gr.Markdown()
                check_models_new_version_log_md = gr.HTML(
                    '正在检查模型，详细进度可在运行窗口查看。'
                )

    # ====events====
    check_models_new_version_btn.click(
        model_action_civitai.check_models_new_version_to_md,
        inputs=model_types_ckbg,
        outputs=check_models_new_version_log_md
    )

    js_dl_model_new_version_btn = gr.Button(
        value='下载模型新版本',
        visible=False,
        elem_id="ch_js_dl_model_new_version_btn"
    )

    js_dl_model_new_version_btn.click(
        js_action_civitai.dl_model_new_version,
        inputs=[
            js_msg_txtbox
        ],
        outputs=dl_new_version_log_md
    )

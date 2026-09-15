# 模型助手 · 中文维护版

面向 Forge Classic Neo（绘图界面）的模型管理插件，支持扫描、关联、下载和浏览模型。本仓库派生自 [msdzero 的版本](https://github.com/msdzero/sd-webui-civitai-helper)，保留其功能与历史，并加入中文界面和新版筛选适配。

## 安装

在扩展管理页面选择“从网址安装”，填写：

```text
https://github.com/Nyxlux-bot/sd-webui-civitai-helper.git
```

已有同名插件时不要同时加载两份。备份本地修改后，可以将原安装的更新源改为本仓库，再更新。安装或更新后完整重启绘图服务。

## 这一版的变化

- 模型浏览、模型助手、下载选项、设置、卡片操作及常用提示已中文化；模型名称、接口参数与已有设置键名保留原值。
- 底模目录包含 73 个当前可选底模和 32 个历史底模。系列分组与官方公开源码一致，例如稳定扩散系列集中展示，社区底模独立分组。
- 补齐 23 种模型类型与 8 种排序方式，新增作者、主模型类别和每页数量筛选。选择底模系列后，可继续指定某个训练底模；不指定时搜索整个系列。
- 历史底模默认收起；网站刚新增的底模可直接输入准确名称。可搜索的资源类型不等同于当前绘图界面支持运行的类型。
- 修复中文及特殊字符搜索参数、重新搜索后的分页历史、失败后重试及末页按钮。搜索使用有上限的超时与重试。
- 保留小卡片的常驻操作菜单，结果卡片自适应宽度，说明可展开，图片遵守用户设置的预览分级。
- 支持文本编码器下载到对应目录，并补齐独立扩散模型、条件控制模型和检测模型的类型映射。

## 使用

“模型浏览”用于搜索和选择模型，结果中的“选择版本与下载”会打开助手下载区，实际下载由该区的按钮执行。“模型助手”提供本地扫描、链接关联、单个或批量下载、重复检查及版本更新。

在“设置 › 模型助手”中配置访问密钥、网络代理和预览分级。已有设置继续使用，仓库不包含任何个人密钥、模型列表或本机配置。

## 筛选数据来源

数据核对于 2026-09-16，依据 Civitai（模型网站）的官方公开源码，固定提交为 `3d18e61eea15641cc00471744cbc7577d818ed0d`：

- [底模与系列定义](https://github.com/civitai/civitai/blob/3d18e61eea15641cc00471744cbc7577d818ed0d/packages/civitai-shared/src/basemodel.constants.ts)
- [模型类型](https://github.com/civitai/civitai/blob/3d18e61eea15641cc00471744cbc7577d818ed0d/packages/civitai-db-schema/src/enums.ts)
- [排序定义](https://github.com/civitai/civitai/blob/3d18e61eea15641cc00471744cbc7577d818ed0d/src/server/common/enums.ts)
- [公共搜索接口参数](https://github.com/civitai/civitai/blob/3d18e61eea15641cc00471744cbc7577d818ed0d/src/server/schema/model.schema.ts)

公开源码与线上部署可能存在时间差。本次没有直接操作网站筛选页面，也没有执行真实模型下载；筛选映射、请求参数、分页及响应处理通过本地模拟响应测试。

## 开发验证

在绘图环境中运行：

```shell
python -m unittest discover -s tests -p "test_*.py" -v
```

卡片脚本测试的依赖在测试目录中单独声明，不影响插件安装：

```shell
cd tests
npm install
npm test
```

`tools/update_catalog.py`（目录更新工具）只读取官方源码文件，不执行外部脚本。将上述源码下载为 `basemodel.constants.ts`、`enums.ts` 和 `common-enums.ts` 后，指定目录和对应提交即可重建目录：

```shell
python tools/update_catalog.py --source-dir SOURCE_DIRECTORY --commit COMMIT_SHA
```

更新后应检查新增分类的中文标签并重新运行测试。

## 原始说明

更早版本的完整说明与原作者信息见 [英文原始文档](README.en.md)。本仓库保留上游提交历史及原有说明，不修改模型本身的授权条件。

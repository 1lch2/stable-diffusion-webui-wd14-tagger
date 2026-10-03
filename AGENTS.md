# WD14 Tagger：Agent 项目上下文

## 项目定位与工作约定

- 本仓库是 Stable Diffusion WebUI Forge / Forge Neo 的 Python 扩展，继续使用 WD14 Tagger 名称；不是独立应用。界面基于 Gradio，API 基于 FastAPI，模型推理使用 ONNX Runtime。
- 默认使用中文沟通，先说明结果，区分代码事实、推断、实际验证和未验证部分。
- 优先在现有架构内做简单修改；保留用户已有改动，不因相邻问题扩大范围。没有明确要求时，不提交、推送或切换分支。
- 本文件是导航和约定，当前代码与用户指令优先。环境版本、缓存位置和服务状态应现场检查，不把旧会话结果当作当前验收。

## 当前模型范围

模型在 `tagger/utils.py` 的 `interrogators` 中注册，字典键是 API 模型标识，实例的 `name` 是界面显示名称。

| API 标识 | 实现 | HuggingFace 仓库 |
| --- | --- | --- |
| `wd-eva02-large-tagger-v3` | `WaifuDiffusionInterrogator` | `SmilingWolf/wd-eva02-large-tagger-v3` |
| `pixai-tagger-v1.0` | `PixAIInterrogator` | `bdsqlsz/pixai-tagger-v1.0-ONNX` |

- WD 系列仅保留 WD EVA02-Large v3；原仓库支持的其他 Tagger 已移除，PixAI 是本分支新增支持。
- 本地 ONNX 自动扫描及 `--onnxtagger-path` 已移除。不要根据历史 README 或旧比较文档恢复这些功能，除非用户要求。
- 两个模型均按需加载，`interrogate()` 返回 `(ratings, tags)` 两个置信度字典。单图、批量和 API 复用这些实现。

## 关键文件与调用路径

| 文件 | 职责 |
| --- | --- |
| `scripts/tagger.py` | Forge 扩展入口，注册界面、设置和 API 回调 |
| `tagger/ui.py` | Gradio 页面、事件绑定、单图/批量提交、结果显示 |
| `tagger/interrogator.py` | 下载、ONNX 会话、模型预处理和推理、卸载，以及单图/批量公共流程 |
| `tagger/utils.py` | 模型注册与模型列表 |
| `tagger/uiset.py` | `IOData` 管理图片与输出路径；`QData` 管理查询缓存、标签过滤、评级、JSON 数据库和标签文件 |
| `tagger/settings.py` | Forge 设置项与默认模型缓存目录 |
| `tagger/api.py`、`tagger/api_models.py` | `/tagger/v1` 接口及请求/响应模型 |
| `tagger/dbimutils.py` | 透明背景处理及 WD 图像缩放工具 |
| `style.css`、`javascript/` | 界面样式与前端交互 |
| `install.py`、`requirements.txt`、`preload.py` | 扩展依赖安装与启动参数 |

单图路径：按钮点击 → `on_interrogate_image_submit()` → 模型实例的 `interrogate_image()` → 缓存命中或 `interrogate()` → `QData` 过滤与汇总 → 界面输出。排查结果不变时，注意查询缓存以图片内容哈希和模型名称区分。

API 单图调用直接进入模型的 `interrogate()`，按请求中的 `threshold` 筛选标签。接口为 `GET /tagger/v1/interrogators`、`POST /tagger/v1/interrogate` 和 `POST /tagger/v1/unload-interrogators`；评级不受该标签阈值筛选。

## 必须保留的界面行为

- 上传、拖入、替换或清空单图，只更新上传组件；不自动加载模型或推理。单图推理仅由 `image_submit.click` 触发，不要重新绑定 `image.change`、`upload` 或 `input` 到推理函数。
- 单图上传组件使用 `elem_id='tagger-single-image'`，`style.css` 将其高度限制为 `50vh`，图片按比例适配。样式应限定在此组件内。
- 预设行及保存、加载实现已移除，不读取旧预设文件。界面默认选择 WD EVA02 Large，阈值为 0.3。
- PixAI 专属控件仅在选中该模型时显示；默认按类别过滤（general 0.17、character 0.27、style 0.15、copyright 0.24、meta 0.17、rating 0.41）。「使用全局阈值」默认关闭，全局值默认 0.2，开启后包含 rating 在内全部类别使用全局值。单图和批量在提交时读取阈值，缓存仍存原始置信度。HTTP API 保留原有 threshold 契约。
- 多个界面操作使用七项 `COMMON_OUTPUT`。修改事件或错误处理时检查返回项数及 Forge 包装器的错误路径，避免原始错误被 Gradio 输出数量错误掩盖。

## 两种模型的推理差异

- **WD EVA02 Large**：下载 `model.onnx` 和 `selected_tags.csv`；透明背景转白色、RGB 转 BGR、补白边为正方形后缩放，输入为 NHWC float32。输出直接作为置信度；CSV 前四项是评级。
- **PixAI**：下载 `model.onnx`、`config.json` 和 `preprocessor_config.json`。预处理遵循模型仓库的 `tagger_pipeline.py`：RGB、透明背景转白色、torchvision 张量缩放、等比例缩放到配置尺寸（当前为 1008）、居中补黑边、归一化到 `[-1, 1]`，输入为 NCHW。
- PixAI 的 ONNX 输出为 logits，必须做 sigmoid；标签顺序和分类区间由 `config.json` 的 `tags`、`tags_split` 决定，不能套用 WD 的前四项评级规则。
- PixAI 将 general、character、copyright、style、meta 合并为标签；rating 映射为 general、sensitive、questionable、explicit。保留置信度给现有 UI/API 过滤，不预先应用原仓库的分类阈值。
- 保持 torchvision 的张量缩放行为，不随意替换为 PIL/OpenCV 缩放。PixAI 不需要执行下载仓库中的 Transformers 模型代码。

## 模型文件与运行环境

- 默认缓存是扩展根目录的 `model/`，由 `tagger/settings.py` 根据文件位置计算，不继承 `HF_HOME` 或 `HUGGINGFACE_HUB_CACHE` 的默认位置。
- Forge 已保存的 `tagger_hf_cache_dir` 设置优先于默认值。修改默认路径不会自动覆盖现有设置；排查下载位置时同时检查 Forge 配置。
- 保留 HuggingFace 的 `models--组织--仓库/refs`、`snapshots`、`blobs` 结构；快照可能通过相对符号链接指向 blobs，迁移不能只移动链接。WD 的 `model.json` 路径记录也在所选缓存目录中。
- `model/` 和 `presets/` 已被 Git 忽略。不要提交权重、缓存或个人预设；迁移应校验文件完整性和离线缓存命中。
- WD 当前显式使用 `https://hf-mirror.com`；PixAI 使用 HuggingFace 默认端点，可通过 `HF_ENDPOINT` 配置。排查下载失败要先确认实际端点。
- 复用 Forge 管理的 PyTorch / torchvision，不在扩展 requirements 中重复声明或擅自升级这组依赖。先检查宿主安装声明与实际环境是否满足需要。
- `get_onnxrt()` 根据实际 CUDA 可用性及强制 CPU 选项选择运行时；CUDA 13 自动选择 GPU 包 `>=1.27,<1.31`，CUDA 12 选择 `>=1.21,<1.27`，无 CUDA 时缺包安装 CPU 版。替换前先下载 wheel，遵守 `--skip-install`，支持 `ONNXRUNTIME_PACKAGE` 包版本覆盖；已导入运行时或 CPU/GPU 混装时提示关闭 Forge 后手动处理。GPU 路径预加载宿主 DLL。PyTorch 能看到显卡不代表 ONNX 会话实际使用 CUDA，需检查 `get_available_providers()` 和实际会话的 `get_providers()`。
- 本工作区的 Forge 根目录是 `../..`，通常使用 `../../venv/Scripts/python.exe`。先确认实际解释器，勿用任意系统 Python 安装或验证依赖。宿主的跳过安装选项可能使扩展依赖安装脚本不执行。

## 文档约定

- `README.md` 是中文主文档，标题下链接 `README.en.md`；功能变更应同步中英文说明。
- `README.original.md` 保留改写前的原始文档，新 README 在中间小节链接它。
- 韩语版 `README.ko.md` 的入口仅放在原始 README 中，其英文入口也指回原始 README。归档和历史资料不代表当前支持范围，不随当前功能改写。

## 验证方式与边界

- 验证与改动风险匹配；少写单测，优先真实流程及失败场景，不写仅检查数据格式或数值的测试。纯文档修改检查链接、内容及差异即可。
- Python 修改可在扩展根目录运行 `../../venv/Scripts/python.exe -m compileall -q tagger scripts`，并运行 `git diff --check`。语法通过不等于 Forge 启动或推理通过。
- 验证模型时优先复用现有缓存；`HF_HUB_OFFLINE=1` 或下载函数的 `local_files_only=True` 可检查离线命中，避免重复下载大权重。
- 根据修改选择必要场景：上传不触发推理、按钮按当前模型推理、透明/非正方形图片、批量输出、卸载后重载、下载失败后重试。事件和布局变更应尽可能在真实 Forge 页面验证。
- 单独导入插件可能缺少 Forge 的 `modules` 上下文；模拟宿主或推理会话只能算隔离验证，不能声称浏览器端到端验收。真实模型 CPU 推理也不代表 GPU 路径通过。
- 既往会话曾验证两个模型从项目 `model/` 离线完成 CPU 推理；50vh 布局和移除上传自动推理当时只做了静态检查。后续应按实际改动重新确认，不将这些记录作为当前通过结论。

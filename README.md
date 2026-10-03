# Stable Diffusion Web UI WD14 Tagger

[English](README.en.md)

为 Stable Diffusion WebUI Forge / Forge Neo 提供图像标签识别：上传单张图片或批量读取本地目录，输出标签、置信度和内容评级，也可通过 HTTP API 调用。

本项目继续沿用 **WD14 Tagger** 名称。WD Tagger 系列现仅保留表现最好的 **WD EVA02-Large Tagger v3**，原始仓库支持的其他 Tagger 均已移除；本分支另外新增了 **PixAI Tagger v1.0 ONNX** 支持。它依赖 Forge 的运行环境，不是独立应用。

## 支持的模型

| 界面名称                 | API 模型标识               | 模型来源                                                                                            |
| ------------------------ | -------------------------- | --------------------------------------------------------------------------------------------------- |
| WD EVA02-Large Tagger v3 | `wd-eva02-large-tagger-v3` | [SmilingWolf/wd-eva02-large-tagger-v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3) |
| PixAI Tagger v1.0        | `pixai-tagger-v1.0`        | [bdsqlsz/pixai-tagger-v1.0-ONNX](https://huggingface.co/bdsqlsz/pixai-tagger-v1.0-ONNX)             |

PixAI 使用社区转换的 ONNX 权重，原模型来自 [pixai-labs/pixai-tagger-v1.0](https://huggingface.co/pixai-labs/pixai-tagger-v1.0)。首次使用会下载约 1.98 GB 的 `model.onnx`，以及 `config.json`、`preprocessor_config.json`。

两个模型分别使用各自的预处理流程。PixAI 按仓库实现进行 RGB 转换、透明背景转白色、等比例缩放、补黑边及归一化，再将 ONNX 输出转换为标签置信度。其 general、character、copyright、style、meta 标签合并到标签结果中，rating 单独输出为 general、sensitive、questionable、explicit。

旧版 ViT、ConvNeXT、SwinV2、MOAT 等模型及本地 ONNX 自动扫描已移除，`--onnxtagger-path` 参数不再支持。已有的旧模型文件不会自动删除。

## 安装与更新

1. 在 Forge 的 **Extensions → Install from URL** 中输入本仓库地址：
   ```text
   https://github.com/1lch2/stable-diffusion-webui-wd14-tagger
   ```
2. 安装完成后，完全退出并重新启动 Forge。
3. 打开 **Tagger** 标签页，在 **Interrogator** 中选择模型。

也可以在 Forge 根目录手动安装：

```sh
git clone https://github.com/1lch2/stable-diffusion-webui-wd14-tagger.git extensions/stable-diffusion-webui-wd14-tagger
```

扩展安装脚本会安装 `requirements.txt` 中的依赖。如果启动配置跳过了扩展依赖安装，可在 Forge 根目录用其自身的 Python 环境安装。Windows 虚拟环境示例：

```powershell
.\venv\Scripts\python.exe -m pip install -r .\extensions\stable-diffusion-webui-wd14-tagger\requirements.txt
```

更新扩展后也需要重启 Forge。默认预设若仍选择已移除的模型，界面初始化时会回退到 WD EVA02 Large。

## 使用方式

### 单张图片

1. 打开 **Single process**，在 **Source** 上传图片。
2. 选择 **Interrogator**，设置 **Weight threshold**。
3. 点击 **Interrogate image**，在 **Ratings and included tags** 查看标签与评级置信度；被过滤的标签显示在 **Excluded tags**。

阈值越高，保留的标签越少。PixAI 同样使用界面阈值，不预先应用原模型的分类阈值，因此可以调低阈值查看更多标签。

### 批量处理

1. 打开 **Batch from directory**，输入图片目录。
2. 如需递归扫描子目录，使用包含 `**` 的路径模式，例如 Windows 下的 `D:\images\**\*`，并开启 Tagger 设置中的递归扫描选项。
3. 设置 **Output directory**；留空时，标签文件默认写入图片所在位置。
4. 按需勾选 **Save to tags files**，点击 **Interrogate**。

默认标签文件与图片同名，扩展名为 `.txt`。输出文件名格式、是否写入权重、JSON 查询数据库的自动读写等选项可在 **Settings → Tagger** 中配置。

### 标签整理与模型卸载

- 通过 **Additional tags**、**Keep tag**、**Exclude tag** 以及搜索替换选项整理标签。
- 使用 **Preset** 保存和加载常用设置。
- **Combine interrogations** 可累积查询结果。
- 勾选 **Unload model after running** 可在界面任务完成后卸载模型，也可点击 **Unload all interrogate models** 手动卸载。

## 原始文档

本分支改写前随仓库保留的说明已归档到 [原始 README](README.original.md)，其中保留了对应的韩语版入口及历史资料链接。归档文档中的旧模型、安装方式和截图仅供参考，当前功能以本页为准。

## 模型下载与运行环境

加载时优先读取所选缓存目录中的本地文件，命中后不联系 HuggingFace；只有缺失的文件才会联网下载。已有缓存不会自动检查远端更新。控制台会分别显示本地文件路径或缓存缺失后的下载提示。

- **缓存目录**：默认保存到本扩展根目录的 `model/`，不再从 `HF_HOME` 或 `HUGGINGFACE_HUB_CACHE` 继承默认位置。目录内保留 HuggingFace 的 `models--组织--仓库/snapshots/…` 缓存结构，权重不会纳入 Git。需要其他位置时，可在 **Settings → Tagger → HuggingFace cache directory** 中修改；已保存的自定义路径优先于默认值。
- **下载端点**：WD EVA02 Large 保留原有的 `https://hf-mirror.com` 下载端点；PixAI 使用 HuggingFace 默认端点，可在启动 Forge 前通过 `HF_ENDPOINT` 指定镜像。
- **推理设备**：两个模型均使用 ONNX Runtime。默认尝试 CUDA，再回退 CPU；CPU 启动选项也可强制使用 CPU。实际是否使用 GPU 取决于 ONNX Runtime 是否提供并能加载 CUDA 执行后端，仅 PyTorch 能识别显卡并不足以保证 ONNX 使用 GPU。
- **ONNX Runtime 安装**：默认复用已安装的运行时。有可用 NVIDIA CUDA 设备且未强制 CPU 时，优先使用 GPU 版；缺失 GPU 版或版本不匹配时，根据 Forge 的 PyTorch CUDA 版本自动选择安装包（CUDA 13：`>=1.27,<1.31`；CUDA 12：`>=1.21,<1.27`）。无 CUDA 时缺包安装 CPU 版。替换前先下载 wheel，再卸载旧版，避免 CPU/GPU 两个发行包混装；可用 `ONNXRUNTIME_PACKAGE` 指定包版本。`--skip-install` 会禁止自动安装；进程已导入 ONNX 或存在混装时，会提示关闭 Forge 后手动处理并重启。其他 CUDA 主版本需手动安装匹配版本。
- **PixAI 预处理**：复用 Forge 本体安装和管理的 `torchvision` / PyTorch，扩展 requirements 不再单独声明这两项。模型推理本身仍由 ONNX Runtime 执行，无需加载仓库中的 Transformers 模型代码。

## HTTP API

扩展注册以下接口。地址和端口以实际 Forge 服务为准；若启用了 `api_auth`，请求需要提供对应的 HTTP Basic 认证。

| 方法 | 路径                              | 用途                     |
| ---- | --------------------------------- | ------------------------ |
| GET  | `/tagger/v1/interrogators`        | 获取可用模型标识         |
| POST | `/tagger/v1/interrogate`          | 识别图片                 |
| POST | `/tagger/v1/unload-interrogators` | 卸载所有已加载的标签模型 |

单图识别请求示例：

```json
{
  "image": "<图片的 Base64 编码>",
  "model": "pixai-tagger-v1.0",
  "threshold": 0.35
}
```

响应中的 `caption.tag` 为标签及置信度，`caption.rating` 为评级及置信度。`threshold` 只筛选标签，省略时默认为 `0.0`。单图调用无需填写 `queue` 和 `name_in_queue`。

## 常见问题

- **下载失败**：查看控制台中实际失败的文件和下载端点，检查网络与缓存目录权限。PixAI 和 WD 使用的默认端点不同。
- **只有 CPU 推理**：查看 ONNX Runtime 的执行后端与控制台日志；安装 CPU 版运行时不会提供 CUDA 后端。调整运行时环境后需要重启 Forge。
- **没有期望的标签**：检查所选模型、阈值、排除标签和最大显示数量；两个模型的标签集合及置信度分布不同。
- **缺少 Python 依赖**：使用启动 Forge 的同一个 Python 环境安装 requirements，再重启。

## 致谢与授权

本扩展沿用 [stable-diffusion-webui-wd14-tagger](https://github.com/picobyte/stable-diffusion-webui-wd14-tagger) 的代码与工作流程。感谢 SmilingWolf、PixAI Labs、ONNX 转换作者 bdsqlsz，以及原项目贡献者。

原仓库将代码声明为 Public domain，但借用的代码（例如 `dbimutils.py`）除外；模型权重和相关文件的授权以各自模型仓库为准。

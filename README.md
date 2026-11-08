# Stable Diffusion Web UI WD14 Tagger

[English](README.en.md)

适用于 Stable Diffusion WebUI Forge / Forge Neo 的图像反推打标插件，支持单图识别、本地目录批量打标及 HTTP API 调用。本分支精简了旧版冗余模型，仅保留效果最好的 **WD EVA02-Large Tagger v3**，并新增了 **PixAI Tagger v1.0 (Mixed BF16)** 支持。

## 支持的模型

| 界面名称 | API 模型标识 | 推理后端 | 模型来源 |
| --- | --- | --- | --- |
| WD EVA02-Large Tagger v3 | `wd-eva02-large-tagger-v3` | ONNX Runtime | [SmilingWolf/wd-eva02-large-tagger-v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3) |
| PixAI Tagger v1.0 | `pixai-tagger-v1.0` | PyTorch SDPA | [DraconicDragon/pixai-tagger-v1.0-mixed-bf16](https://huggingface.co/DraconicDragon/pixai-tagger-v1.0-mixed-bf16) |

**PixAI Tagger 说明**：首次使用时会自动下载约 1.04 GB 的混合 BF16 Safetensors 权重（原模型来自 [pixai-labs/pixai-tagger-v1.0](https://huggingface.co/pixai-labs/pixai-tagger-v1.0)）。模型直接复用 Forge 环境的 PyTorch（优先使用 CUDA），将其识别的 general、character、copyright、style、meta 标签合并输出，rating（general、sensitive、questionable、explicit）单独输出。

## 安装

在 Forge 的 **Extensions → Install from URL** 中输入以下地址安装，或直接 clone 到 `extensions` 目录：

```bash
git clone https://github.com/1lch2/stable-diffusion-webui-wd14-tagger.git extensions/stable-diffusion-webui-wd14-tagger

```

安装或更新后需**完全重启 Forge**。插件启动时会自动安装依赖；若启动参数禁用了扩展依赖安装，可在 Forge 根目录下手动执行：

```powershell
.\venv\Scripts\python.exe -m pip install -r .\extensions\stable-diffusion-webui-wd14-tagger\requirements.txt

```

## 使用指南

**单图与阈值设置**
在 **Single process** 上传图片并选择模型，点击 **Interrogate image** 即可输出标签与评级。阈值越高，过滤越严格，调整阈值后再次点击按钮会直接基于缓存重新过滤，无需重复推理。**WD EVA02 Large** 默认使用 `0.3` 的全局阈值；**PixAI** 默认启用分类阈值（general `0.17`、character `0.27`、style `0.15`、copyright `0.24`、meta `0.17`、rating `0.41`），也可勾选切换为统一的全局阈值（默认 `0.2`）。

**批量打标**
在 **Batch from directory** 输入图片文件夹路径，勾选 **Save to tags files** 后点击 **Interrogate**，默认在原图同目录下生成同名 `.txt` 标签文件。如需递归处理子目录，请在 **Settings → Tagger** 中开启递归选项，并使用包含 `**` 的路径格式（如 `D:\images\**\*`）。

**标签处理与显存管理**
界面下方支持补充、保留、排除指定标签或执行正则替换，开启 **Combine interrogations** 可累积多次打标结果。勾选 **Unload model after running** 可在任务完成后自动释放显存，或点击 **Unload all interrogate models** 手动卸载。

## 下载与环境配置

* **缓存路径**：模型默认下载至本插件目录下的 `model/` 文件夹（不读取系统 `HF_HOME` 环境变量），可在 **Settings → Tagger → HuggingFace cache directory** 中自定义路径。本地已有文件时不会联网检查。
* **下载镜像**：WD 模型默认走 `[https://hf-mirror.com](https://hf-mirror.com)` 下载；PixAI 模型使用 HuggingFace 官方源，国内网络建议在启动 Forge 前配置环境变量 `HF_ENDPOINT=[https://hf-mirror.com](https://hf-mirror.com)`。
* **ONNX 环境（仅 WD 模型需要）**：插件会根据 Forge 的 PyTorch CUDA 版本（支持 CUDA 12 / 13）自动安装匹配的 `onnxruntime-gpu`。如需指定版本，可通过环境变量 `ONNXRUNTIME_PACKAGE` 覆盖。

## HTTP API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/tagger/v1/interrogators` | 获取可用模型标识 |
| POST | `/tagger/v1/interrogate` | 识别单张图片 |
| POST | `/tagger/v1/unload-interrogators` | 卸载所有已加载的打标模型 |

**`POST /tagger/v1/interrogate` 请求示例：**

```json
{
  "image": "<Base64 编码的图片>",
  "model": "pixai-tagger-v1.0",
  "threshold": 0.35
}

```

返回结果中 `caption.tag` 为标签字典，`caption.rating` 为分级置信度（`threshold` 仅过滤普通标签，不过滤 rating）。

## 致谢与历史归档

本项目基于 [picobyte/stable-diffusion-webui-wd14-tagger](https://github.com/picobyte/stable-diffusion-webui-wd14-tagger) 修改，旧版文档已归档至 [README.original.md](README.original.md)。感谢 SmilingWolf、PixAI Labs、DraconicDragon、bdsqlsz 及原项目贡献者。代码遵循原仓库 Public domain 声明，模型权重授权以各自仓库为准。

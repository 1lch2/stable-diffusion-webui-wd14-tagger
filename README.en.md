# Stable Diffusion Web UI WD14 Tagger

[简体中文](README.md)

An image-tagging extension for Stable Diffusion WebUI Forge / Forge Neo. It supports single-image tagging, batch tagging from a local directory, and HTTP API requests. This branch streamlines the original project and supports **WD EVA02-Large Tagger v3** and **PixAI Tagger v1.0 (Mixed BF16)**.

## Supported models

| Display name | API model identifier | Inference backend | Model source |
| --- | --- | --- | --- |
| WD EVA02-Large Tagger v3 | `wd-eva02-large-tagger-v3` | ONNX Runtime | [SmilingWolf/wd-eva02-large-tagger-v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3) |
| PixAI Tagger v1.0 | `pixai-tagger-v1.0` | PyTorch SDPA | [DraconicDragon/pixai-tagger-v1.0-mixed-bf16](https://huggingface.co/DraconicDragon/pixai-tagger-v1.0-mixed-bf16) |

**About PixAI Tagger:** On first use, the extension automatically downloads approximately 1.04 GB of mixed BF16 Safetensors weights. The model is based on [pixai-labs/pixai-tagger-v1.0](https://huggingface.co/pixai-labs/pixai-tagger-v1.0). It uses the PyTorch installation provided by Forge and supports the categories `general`, `character`, `copyright`, `style`, `meta`, and `rating`.

## Installation

In Forge, open **Extensions → Install from URL** and enter the following URL, or clone the repository into the `extensions` directory:

```bash
git clone https://github.com/1lch2/stable-diffusion-webui-wd14-tagger.git extensions/stable-diffusion-webui-wd14-tagger
```

Fully restart Forge after installing or updating the extension. Dependencies are installed automatically at startup. If extension dependency installation is disabled in your startup options, install them manually from the Forge root directory:

```powershell
.\venv\Scripts\python.exe -m pip install -r .\extensions\stable-diffusion-webui-wd14-tagger\requirements.txt
```

## Usage

**Single image and thresholds**  
In **Single process**, upload an image and select a model, then click **Interrogate image** to display tags and ratings. Higher thresholds filter out more tags. After changing a threshold, click the button again to apply it to the cached results without rerunning inference.

- **WD EVA02 Large**: The default weight threshold is `0.3`.
- **PixAI**: Category-specific thresholds are used by default: general `0.17`, character `0.27`, style `0.15`, copyright `0.24`, meta `0.17`, and rating `0.41`. The **Use global threshold** option is off by default. When enabled, the global threshold (default `0.2`) is applied to every category, including rating.

**Batch tagging**  
In **Batch from directory**, enter an image folder and click **Interrogate**. Enable **Save to tags files** to write a `.txt` tag file with the same name as each image, by default in the image's directory. To process subdirectories recursively, use a path pattern containing `**` (for example, `D:\images\**\*`) and enable recursive scanning in the settings.

**Tag editing and model memory**  
The controls below the interface let you add, keep, or exclude tags and perform regular-expression replacements. Enable **Combine interrogations** to accumulate results from multiple interrogations. Enable **Unload model after running** to unload the model when a task finishes, or use **Unload all interrogate models** to unload models manually.

## Downloads and environment

- **Cache directory**: Models are downloaded by default to the `model/` directory inside this extension; the system `HF_HOME` environment variable is not used. Change the location under **Settings → Tagger → HuggingFace cache directory**.
- **Download endpoints**: WD models use [https://hf-mirror.com](https://hf-mirror.com) by default. PixAI uses the official HuggingFace endpoint. For networks that cannot reach it, set `HF_ENDPOINT=https://hf-mirror.com` before starting Forge.
- **ONNX environment (WD only)**: The extension automatically installs an `onnxruntime-gpu` version matching Forge's PyTorch CUDA version (CUDA 12 and 13 are supported). PixAI uses PyTorch and does not require ONNX Runtime.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/tagger/v1/interrogators` | List available model identifiers |
| POST | `/tagger/v1/interrogate` | Tag a single image |
| POST | `/tagger/v1/unload-interrogators` | Unload all loaded tagger models |

**Example `POST /tagger/v1/interrogate` request:**

```json
{
  "image": "<Base64-encoded image>",
  "model": "pixai-tagger-v1.0",
  "threshold": 0.35
}
```

In the response, `caption.tag` contains the tag dictionary and `caption.rating` contains rating scores. The `threshold` filters tags only; it does not filter ratings.

## Credits and archive

This project is based on [picobyte/stable-diffusion-webui-wd14-tagger](https://github.com/picobyte/stable-diffusion-webui-wd14-tagger). The previous documentation is archived in [README.original.md](README.original.md).

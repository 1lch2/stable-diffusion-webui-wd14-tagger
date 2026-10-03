# Stable Diffusion Web UI WD14 Tagger

[简体中文](README.md)

Image tagging for Stable Diffusion WebUI Forge / Forge Neo. Upload an image or process a local directory to obtain tags, confidence scores, and content ratings. HTTP API access is also available.

The project retains the **WD14 Tagger** name. The WD Tagger family is now represented only by its best-performing model, **WD EVA02-Large Tagger v3**. All other taggers supported by the original repository have been removed, and this fork adds support for **PixAI Tagger v1.0 ONNX**. It requires a Forge environment and is not a standalone application.

## Supported models

| Display name             | API model identifier       | Model repository                                                                                    |
| ------------------------ | -------------------------- | --------------------------------------------------------------------------------------------------- |
| WD EVA02-Large Tagger v3 | `wd-eva02-large-tagger-v3` | [SmilingWolf/wd-eva02-large-tagger-v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3) |
| PixAI Tagger v1.0        | `pixai-tagger-v1.0`        | [bdsqlsz/pixai-tagger-v1.0-ONNX](https://huggingface.co/bdsqlsz/pixai-tagger-v1.0-ONNX)             |

PixAI uses a community ONNX conversion of [pixai-labs/pixai-tagger-v1.0](https://huggingface.co/pixai-labs/pixai-tagger-v1.0). On first use, it downloads `model.onnx` (approximately 1.98 GB), `config.json`, and `preprocessor_config.json`.

Each model uses its own preprocessing. PixAI follows the repository implementation: RGB conversion, white compositing for transparency, resizing with the aspect ratio preserved, black padding, and normalization. ONNX outputs are then converted to confidence scores. The general, character, copyright, style, and meta categories are combined into the tag results; ratings are returned separately as general, sensitive, questionable, and explicit.

Legacy ViT, ConvNeXT, SwinV2, MOAT, and other models have been removed, along with local ONNX discovery and the `--onnxtagger-path` argument. Previously downloaded model files are not deleted automatically.

## Installation and updates

1. In Forge, open **Extensions → Install from URL** and enter:
   ```text
   https://github.com/1lch2/stable-diffusion-webui-wd14-tagger
   ```
2. Fully exit and restart Forge after installation.
3. Open the **Tagger** tab and select a model under **Interrogator**.

Alternatively, install manually from the Forge root directory:

```sh
git clone https://github.com/1lch2/stable-diffusion-webui-wd14-tagger.git extensions/stable-diffusion-webui-wd14-tagger
```

The extension installer installs the dependencies in `requirements.txt`. If your startup configuration skips extension dependency installation, install them with Forge's own Python environment from the Forge root directory. Example for a Windows virtual environment:

```powershell
.\venv\Scripts\python.exe -m pip install -r .\extensions\stable-diffusion-webui-wd14-tagger\requirements.txt
```

Restart Forge after updating the extension as well. If a saved default preset selects a removed model, the interface falls back to WD EVA02 Large during initialization.

## Usage

### Single image

1. Open **Single process** and upload an image under **Source**.
2. Select an **Interrogator** and set **Weight threshold**.
3. Click **Interrogate image**. View tags and rating scores under **Ratings and included tags**; filtered tags appear under **Excluded tags**.

Higher thresholds retain fewer tags. PixAI also uses the interface threshold instead of applying the original model's category thresholds beforehand, so you can lower the threshold to see more tags.

### Batch processing

1. Open **Batch from directory** and enter an image directory.
2. To include subdirectories, use a path pattern containing `**`, such as `D:\images\**\*` on Windows, and enable recursive scanning in the Tagger settings.
3. Set **Output directory**. When left empty, tag files default to the image locations.
4. Enable **Save to tags files** as needed and click **Interrogate**.

By default, tag files share the image basename and use the `.txt` extension. **Settings → Tagger** includes options for output filenames, writing weights, and automatically reading and writing the JSON query database.

### Tag editing and model unloading

- Organize tags with **Additional tags**, **Keep tag**, **Exclude tag**, and the search/replace controls.
- Save and load frequently used settings with **Preset**.
- Use **Combine interrogations** to accumulate query results.
- Enable **Unload model after running** to unload the model after an interface task, or click **Unload all interrogate models** to unload manually.

## Original documentation

The README shipped with this branch before the rewrite is preserved as the [original README](README.original.md). It retains the entry point to its Korean version and links to historical material. Legacy models, installation instructions, and screenshots in the archive are for reference; this page describes the current functionality.

## Model downloads and runtime

Loading checks the selected local cache first and does not contact HuggingFace for cached files. Only missing files are downloaded. Existing cached files are not automatically checked for remote updates. The console reports either the local file path or a cache miss followed by a download.

- **Cache directory**: Defaults to `model/` inside this extension, without inheriting the default location from `HF_HOME` or `HUGGINGFACE_HUB_CACHE`. It retains HuggingFace's `models--organization--repository/snapshots/…` cache structure, and weights are excluded from Git. To use another location, change **Settings → Tagger → HuggingFace cache directory**; a saved custom path takes precedence over the default.
- **Download endpoints**: WD EVA02 Large retains the `https://hf-mirror.com` endpoint. PixAI uses the default HuggingFace endpoint; set `HF_ENDPOINT` before starting Forge to use a mirror.
- **Inference device**: Both models use ONNX Runtime. CUDA is tried first, with CPU fallback; CPU startup options can also force CPU execution. GPU inference requires an ONNX Runtime CUDA execution provider that can actually load. PyTorch detecting a GPU alone does not guarantee ONNX GPU execution.
- **ONNX Runtime installation**: Reuse the installed runtime when suitable. With an available NVIDIA CUDA device and no forced CPU option, prefer the GPU package; install or replace it when missing or incompatible with Forge's PyTorch CUDA version (CUDA 13: `>=1.27,<1.31`; CUDA 12: `>=1.21,<1.27`). Without CUDA, install the CPU package if no runtime exists. Download the wheel before removing the old distribution to avoid CPU/GPU package overlap. `ONNXRUNTIME_PACKAGE` can specify a package version. `--skip-install` disables installation. If ONNX is already imported or both distributions are installed, close Forge, fix the environment manually, and restart. Other CUDA major versions require a matching manual installation.
- **PixAI preprocessing**: Reuses `torchvision` / PyTorch installed and managed by Forge. The extension requirements do not separately declare these packages. Model inference still runs through ONNX Runtime and does not load the repository's Transformers model code.

## HTTP API

The extension registers the following endpoints. Use your actual Forge host and port. If `api_auth` is enabled, supply the corresponding HTTP Basic credentials.

| Method | Path                              | Purpose                          |
| ------ | --------------------------------- | -------------------------------- |
| GET    | `/tagger/v1/interrogators`        | List available model identifiers |
| POST   | `/tagger/v1/interrogate`          | Tag an image                     |
| POST   | `/tagger/v1/unload-interrogators` | Unload all loaded tagger models  |

Example single-image request:

```json
{
  "image": "<Base64-encoded image>",
  "model": "pixai-tagger-v1.0",
  "threshold": 0.35
}
```

The response contains tags and scores in `caption.tag`, and rating scores in `caption.rating`. `threshold` filters tags only and defaults to `0.0` when omitted. Single-image requests do not need `queue` or `name_in_queue`.

## Troubleshooting

- **Download failure**: Check the failing file and endpoint in the console, network access, and cache directory permissions. PixAI and WD use different default endpoints.
- **CPU-only inference**: Check the ONNX Runtime execution providers and console logs. A CPU runtime package does not provide CUDA execution. Restart Forge after changing the runtime environment.
- **Missing expected tags**: Check the selected model, threshold, excluded tags, and maximum display count. The models have different tag vocabularies and confidence distributions.
- **Missing Python dependencies**: Install requirements with the same Python environment that starts Forge, then restart it.

## Credits and licensing

This extension builds on the code and workflows of [stable-diffusion-webui-wd14-tagger](https://github.com/picobyte/stable-diffusion-webui-wd14-tagger). Thanks to SmilingWolf, PixAI Labs, ONNX conversion author bdsqlsz, and the original project contributors.

The original repository declares its code Public domain, except borrowed code such as `dbimutils.py`. Model weights and associated files are governed by their respective model repositories.

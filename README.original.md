# WD14 Tagger extension for SD WebUI Forge Neo

**Note: This is a modified fork for Web UI Forge Neo instead of original SD Web UI**

## Tagger for [Automatic1111's WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

Interrogate booru style tags for single or multiple image files using various models, such as DeepDanbooru.

[한국어를 사용하시나요? 여기에 한국어 설명서가 있습니다!](README.ko.md)

## What this fork changes

### Model update 更新模型

Added wd14-swinv2-v2 and wd-eva02-large-tagger-v3 model from [SmilingWolf](https://huggingface.co/SmilingWolf)

Added huggingface mirror for users in China.

增加了 wd14-swinv2-v2， wd-eva02-large-tagger-v3 两个新的 tagger 模型。

加入了国内的 huggingface 镜像，方便中国用户在webui里直接下载模型。

### Removed old models and tensorflow 移除了旧模型和tensorflow依赖

Tensorflow has conflict with the newest webui-forge-classic-neo. I removed the related code and fix the compatiablity with the webui-forge-neo

Tensorflow 和最新的 webui-forge-classic-neo 有依赖冲突。我把旧模型和tensorflow依赖一块移除了，修复了和webui-forge-neo的兼容性。

## Disclaimer

I didn't make any models, and most of the code was heavily borrowed from the [DeepDanbooru](https://github.com/KichangKim/DeepDanbooru) and MrSmillingWolf's tagger.

## Installation

1. _Extensions_ -> _Install from URL_ -> Enter URL of this repository -> Press _Install_ button
   - or clone this repository under `extensions/`
     ```sh
     $ git clone https://github.com/picobyte/stable-diffusion-webui-wd14-tagger.git extensions/tagger
     ```

1. _(optional)_ Add interrogate model
   - #### [_Waifu Diffusion 1.4 Tagger by MrSmilingWolf_](docs/what-is-wd14-tagger.md)

     Downloads automatically from the [HuggingFace repository](https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger) the first time you run it.

   - #### _DeepDanbooru_
     1. Various model files can be found below.
        - [DeepDanbooru models](https://github.com/KichangKim/DeepDanbooru/releases)
        - [e621 model by 🐾Zack🐾#1984](https://discord.gg/BDFpq9Yb7K)
          _(link contains NSFW contents!)_

     1. Move the project folder containing the model and config to `models/deepdanbooru`

     1. The file structure should look like:
        ```
        models/
        └╴deepdanbooru/
          ├╴deepdanbooru-v3-20211112-sgd-e28/
          │ ├╴project.json
          │ └╴...
          │
          ├╴deepdanbooru-v4-20200814-sgd-e30/
          │ ├╴project.json
          │ └╴...
          │
          ├╴e621-v3-20221117-sgd-e32/
          │ ├╴project.json
          │ └╴...
          │
          ...
        ```

1. Start or restart the WebUI.
   - or you can press refresh button after _Interrogator_ dropdown box.
   - "You must close stable diffusion completely after installation and re-run it!"

## Model comparison

[Model comparison](docs/model-comparison.md)

## Screenshot

![Screenshot](docs/screenshot.png)

Artwork made by [hecattaart](https://vk.com/hecattaart?w=wall-89063929_3767)

## Copyright

Public domain, except borrowed parts (e.g. `dbimutils.py`)

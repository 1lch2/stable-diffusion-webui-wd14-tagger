"""Utility functions for the tagger module"""
import os

from typing import List, Dict
from pathlib import Path

from modules import shared, scripts  # pylint: disable=import-error
from modules.shared import models_path  # pylint: disable=import-error

default_onnx_path = Path(models_path, 'TaggerOnnx')
from tagger.preset import Preset  # pylint: disable=import-error
from tagger.interrogator import Interrogator  # pylint: disable=E0401
from tagger.interrogator import WaifuDiffusionInterrogator  # pylint: disable=E0401 # noqa: E501

preset = Preset(Path(scripts.basedir(), 'presets'))

interrogators: Dict[str, Interrogator] = {
    'wd14-vit.v1': WaifuDiffusionInterrogator(
        'WD14 ViT v1',
        repo_id='SmilingWolf/wd-v1-4-vit-tagger'
    ),
    'wd14-vit.v2': WaifuDiffusionInterrogator(
        'WD14 ViT v2',
        repo_id='SmilingWolf/wd-v1-4-vit-tagger-v2',
    ),
    'wd14-convnext.v1': WaifuDiffusionInterrogator(
        'WD14 ConvNeXT v1',
        repo_id='SmilingWolf/wd-v1-4-convnext-tagger'
    ),
    'wd14-convnext.v2': WaifuDiffusionInterrogator(
        'WD14 ConvNeXT v2',
        repo_id='SmilingWolf/wd-v1-4-convnext-tagger-v2',
    ),
    'wd14-convnextv2.v1': WaifuDiffusionInterrogator(
        'WD14 ConvNeXTV2 v1',
        # the name is misleading, but it's v1
        repo_id='SmilingWolf/wd-v1-4-convnextv2-tagger-v2',
    ),
    'wd14-swinv2-v1': WaifuDiffusionInterrogator(
        'WD14 SwinV2 v1',
        # again misleading name
        repo_id='SmilingWolf/wd-v1-4-swinv2-tagger-v2',
    ),
    'wd14-swinv2-v2': WaifuDiffusionInterrogator(
        'WD14 swinv2 tagger v2',
        repo_id='SmilingWolf/wd-v1-4-swinv2-tagger-v2'
    ),
    'wd-eva02-large-tagger-v3': WaifuDiffusionInterrogator(
        'WD EVA02-Large Tagger v3',
        repo_id='SmilingWolf/wd-eva02-large-tagger-v3'
    ),
    'wd-v1-4-moat-tagger.v2': WaifuDiffusionInterrogator(
        'WD14 moat tagger v2',
        repo_id='SmilingWolf/wd-v1-4-moat-tagger-v2'
    ),
}


def refresh_interrogators() -> List[str]:
    """Refreshes the interrogators list"""
    onnx_path = shared.cmd_opts.onnxtagger_path
    if onnx_path is None:
        onnx_path = default_onnx_path
    os.makedirs(onnx_path, exist_ok=True)

    for path in os.scandir(onnx_path):
        print(f"Scanning {path} as onnx model")
        if not path.is_dir():
            print(f"Warning: {path} is not a directory, skipped")
            continue

        onnx_files = [x for x in os.scandir(path) if x.name.endswith('.onnx')]
        if len(onnx_files) != 1:
            print(f"Warning: {path} requires exactly one .onnx model, skipped")
            continue
        local_path = Path(path, onnx_files[0].name)

        csv = [x for x in os.scandir(path) if x.name.endswith('.csv')]
        if len(csv) == 0:
            print(f"Warning: {path} has no selected tags .csv file, skipped")
            continue

        def tag_select_csvs_up_front(k):
            sum(-1 if t in k.name.lower() else 1 for t in ["tag", "select"])

        csv.sort(key=tag_select_csvs_up_front)
        tags_path = Path(path, csv[0])

        if path.name not in interrogators:
            if path.name == 'wd-v1-4-convnextv2-tagger-v2':
                interrogators[path.name] = WaifuDiffusionInterrogator(
                    path.name,
                    repo_id='SmilingWolf/SW-CV-ModelZoo',
                    is_hf=False
                )
            elif path.name == 'Z3D-E621-Convnext':
                interrogators[path.name] = WaifuDiffusionInterrogator(
                    'Z3D-E621-Convnext', is_hf=False)
            else:
                raise NotImplementedError(f"Add {path.name} resolution similar"
                                          "to above here")

        interrogators[path.name].local_model = str(local_path)
        interrogators[path.name].local_tags = str(tags_path)

    return sorted(interrogators.keys())


def split_str(string: str, separator=',') -> List[str]:
    return [x.strip() for x in string.split(separator) if x]

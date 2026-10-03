"""Utility functions for the tagger module"""
from typing import List, Dict
from tagger.interrogator import Interrogator  # pylint: disable=E0401
from tagger.interrogator import WaifuDiffusionInterrogator  # pylint: disable=E0401 # noqa: E501
from tagger.interrogator import PixAIInterrogator

interrogators: Dict[str, Interrogator] = {
    'wd-eva02-large-tagger-v3': WaifuDiffusionInterrogator(
        'WD EVA02-Large Tagger v3',
        repo_id='SmilingWolf/wd-eva02-large-tagger-v3'
    ),
    'pixai-tagger-v1.0': PixAIInterrogator('PixAI Tagger v1.0 Mixed BF16'),
}


def refresh_interrogators() -> List[str]:
    """Return the two supported models without discovering legacy models."""
    return sorted(interrogators.keys())


def split_str(string: str, separator=',') -> List[str]:
    return [x.strip() for x in string.split(separator) if x]

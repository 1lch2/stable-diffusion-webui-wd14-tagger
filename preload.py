""" Preload module for onnxtagger. """
from argparse import ArgumentParser


def preload(parser: ArgumentParser):
    """ Preload module for onnxtagger. """
    parser.add_argument(
        '--onnxtagger-path',
        type=str,
        help='Path to directory with Onnx tagger model(s).'
    )
    # TODO allow using devices in parallel, specified as comma separed list
    parser.add_argument(
        '--additional-device-ids',
        type=str,
        help='Device ID to use. cpu:0, gpu:0 or gpu:1, etc.',
    )

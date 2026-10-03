""" Interrogator class and subclasses for tagger """
import os
from pathlib import Path
import io
import importlib.util
import json
from re import match as re_match
import sys
import subprocess
from importlib.metadata import version, PackageNotFoundError
from typing import Tuple, Dict, Callable
from pandas import read_csv
from PIL import Image, UnidentifiedImageError
from numpy import asarray, float32, expand_dims
from tqdm import tqdm
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError

from modules import shared
from tagger import settings  # pylint: disable=import-error
from tagger.uiset import QData, IOData  # pylint: disable=import-error
from . import dbimutils  # pylint: disable=import-error # noqa

Its = settings.InterrogatorSettings

# select a device to process
use_cpu = getattr(shared.cmd_opts, 'cpu', False) or any(
    device in ('all', 'interrogate')
    for device in getattr(shared.cmd_opts, 'use_cpu', []))

# https://onnxruntime.ai/docs/execution-providers/
# https://github.com/toriato/stable-diffusion-webui-wd14-tagger/commit/e4ec460122cf674bbf984df30cdb10b4370c1224#r92654958
onnxrt_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

if shared.cmd_opts.additional_device_ids is not None:
    m = re_match(r'([cg])pu:\d+$', shared.cmd_opts.additional_device_ids)
    if m is None:
        raise ValueError('--device-id is not cpu:<nr> or gpu:<nr>')
    if m.group(1) == 'c':
        onnxrt_providers.pop(0)
elif use_cpu:
    onnxrt_providers.pop(0)


class Interrogator:
    """ Interrogator class for tagger """
    # the raw input and output.
    input = {
        "cumulative": False,
        "unload_after": False,
        "add": '',
        "keep": '',
        "exclude": '',
        "search": '',
        "replace": '',
        "output_dir": '',
    }
    output = None

    @classmethod
    def flip(cls, key):
        def toggle():
            cls.input[key] = not cls.input[key]
        return toggle

    @staticmethod
    def get_errors() -> str:
        errors = ''
        if len(IOData.err) > 0:
            # write errors in html pointer list, every error in a <li> tag
            errors = IOData.error_msg()
        if len(QData.err) > 0:
            errors += 'Fix to write correct output:<br><ul><li>' + \
                      '</li><li>'.join(QData.err) + '</li></ul>'
        return errors

    @classmethod
    def set(cls, key: str) -> Callable[[str], Tuple[str, str]]:
        def setter(val) -> Tuple[str, str]:
            if key == 'input_glob':
                IOData.update_input_glob(val)
                return (val, cls.get_errors())
            if val != cls.input[key]:
                tgt_cls = IOData if key == 'output_dir' else QData
                getattr(tgt_cls, "update_" + key)(val)
                cls.input[key] = val
            return (cls.input[key], cls.get_errors())

        return setter

    @staticmethod
    def load_image(path: str) -> Image:
        try:
            return Image.open(path)
        except FileNotFoundError:
            print(f'${path} not found')
        except UnidentifiedImageError:
            # just in case, user has mysterious file...
            print(f'${path} is not a  supported image type')
        except ValueError:
            print(f'${path} is not readable or StringIO')
        return None

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = None
        self.tags = None

    def load(self):
        raise NotImplementedError()

    def unload(self) -> bool:
        unloaded = False

        if self.model is not None:
            del self.model
            self.model = None
            unloaded = True
            print(f'Unloaded {self.name}')

        if hasattr(self, 'tags'):
            del self.tags
            self.tags = None

        return unloaded

    def interrogate_image(self, image: Image) -> None:
        sha = IOData.get_bytes_hash(image.tobytes())
        QData.clear(1 - Interrogator.input["cumulative"])

        fi_key = sha + self.name
        count = 0

        if fi_key in QData.query:
            # this file was already queried for this interrogator.
            QData.single_data(fi_key)
        else:
            # single process
            count += 1
            data = ('', '', fi_key) + self.interrogate(image)
            # When drag-dropping an image, the path [0] is not known
            if Interrogator.input["unload_after"]:
                self.unload()

            QData.apply_filters(data)

        model_names = QData.cached_model_names()
        for index, got in QData.in_db.items():
            QData.apply_filters(got, model_names[index])

        Interrogator.output = QData.finalize(count)

    def batch_interrogate_image(self, index: int) -> None:
        # if outputpath is '', no tags file will be written
        if len(IOData.paths[index]) == 5:
            path, out_path, output_dir, image_hash, image = IOData.paths[index]
        elif len(IOData.paths[index]) == 4:
            path, out_path, output_dir, image_hash = IOData.paths[index]
            image = Interrogator.load_image(path)
            # should work, we queried before to get the image_hash
        else:
            path, out_path, output_dir = IOData.paths[index]
            image = Interrogator.load_image(path)
            if image is None:
                return

            image_hash = IOData.get_bytes_hash(image.tobytes())
            IOData.paths[index].append(image_hash)
            if getattr(shared.opts, 'tagger_store_images', False):
                IOData.paths[index].append(image)

            if output_dir:
                output_dir.mkdir(0o755, True, True)
                # next iteration we don't need to create the directory
                IOData.paths[index][2] = ''
        QData.image_dups[image_hash].add(path)

        abspath = str(path.absolute())
        fi_key = image_hash + self.name

        if fi_key in QData.query:
            # this file was already queried for this interrogator.
            i = QData.get_index(fi_key, abspath)
            # this file was already queried and stored
            QData.in_db[i] = (abspath, out_path, '', {}, {})
        else:
            data = (abspath, out_path, fi_key) + self.interrogate(image)
            # also the tags can indicate that the image is a duplicate
            no_floats = sorted(filter(lambda x: not isinstance(x[0], float),
                                      data[3].items()), key=lambda x: x[0])
            sorted_tags = ','.join(f'({k},{v:.1f})' for (k, v) in no_floats)
            QData.image_dups[sorted_tags].add(abspath)
            QData.apply_filters(data)
            QData.had_new = True

    def batch_interrogate(self) -> None:
        """ Interrogate all images in the input list """
        QData.clear(1 - Interrogator.input["cumulative"])

        verb = getattr(shared.opts, 'tagger_verbose', True)
        count = len(QData.query)

        for i in tqdm(range(len(IOData.paths)), disable=verb, desc='Tags'):
            self.batch_interrogate_image(i)

        if Interrogator.input["unload_after"]:
            self.unload()

        count = len(QData.query) - count
        Interrogator.output = QData.finalize_batch(count)

    def interrogate(
        self,
        image: Image
    ) -> Tuple[
        Dict[str, float],  # rating confidences
        Dict[str, float]  # tag confidences
    ]:
        raise NotImplementedError()


def get_onnxrt():
    """Reuse Forge's CUDA libraries and install a missing runtime when allowed."""
    import torch

    global onnxrt_providers
    wants_cuda = ('CUDAExecutionProvider' in onnxrt_providers
                  and torch.cuda.is_available() and torch.version.cuda is not None)

    def installed(package):
        try:
            return version(package)
        except PackageNotFoundError:
            return None

    cpu_version = installed('onnxruntime')
    gpu_version = installed('onnxruntime-gpu')
    # Existing GPU builds must also match Forge's CUDA major version.
    cuda_packages = {'13': 'onnxruntime-gpu>=1.27,<1.31',
                     '12': 'onnxruntime-gpu>=1.21,<1.27'}
    cuda_package = cuda_packages.get(torch.version.cuda.split('.')[0]) if wants_cuda else None
    gpu_mismatch = False
    if wants_cuda and gpu_version and cuda_package:
        from packaging.requirements import Requirement
        gpu_mismatch = gpu_version not in Requirement(cuda_package).specifier
    needs_install = (not (cpu_version or gpu_version)
                     or (wants_cuda and not gpu_version) or gpu_mismatch)
    if cpu_version and gpu_version:
        raise RuntimeError(
            'Both onnxruntime and onnxruntime-gpu are installed. Uninstall both, '
            'reinstall one runtime, then restart Forge to avoid overlapping files.'
        )
    if needs_install:
        if getattr(shared.cmd_opts, 'skip_install', False):
            if not (cpu_version or gpu_version):
                raise RuntimeError('ONNX Runtime is missing and --skip-install is enabled. '
                                   'Install the runtime in Forge Python, then restart.')
            print('[Tagger] CUDA GPU detected, but --skip-install prevents installing '
                  'a matching GPU runtime. Install it manually and restart.')
            if gpu_mismatch:
                wants_cuda = False
        else:
            package = os.environ.get('ONNXRUNTIME_PACKAGE')
            if not package:
                if wants_cuda:
                    cuda_major = torch.version.cuda.split('.')[0]
                    # PyPI CUDA 13 builds start at 1.27; earlier builds use CUDA 12.
                    package = cuda_package
                    if package is None:
                        raise RuntimeError(f'Automatic ONNX installation is not configured for '
                                           f'CUDA {cuda_major}. Set ONNXRUNTIME_PACKAGE to a '
                                           'compatible package or install it manually.')
                else:
                    package = 'onnxruntime'
            if 'onnxruntime' in sys.modules:
                raise RuntimeError('ONNX Runtime is already imported in this Forge process. '
                                   'Install the matching runtime manually with Forge closed, '
                                   'then restart; loaded native modules cannot be replaced safely.')
            from launch import run_pip
            # Download first so a network failure does not remove a working CPU runtime.
            import tempfile
            with tempfile.TemporaryDirectory(prefix='tagger-onnx-') as wheel_dir:
                run_pip(f'download --no-deps --only-binary=:all: "{package}" '
                        f'--dest "{wheel_dir}"', 'Tagger ONNX runtime download')
                wheels = list(Path(wheel_dir).glob('*.whl'))
                if len(wheels) != 1:
                    raise RuntimeError('Expected one downloaded ONNX Runtime wheel.')
                if wants_cuda and not wheels[0].name.startswith('onnxruntime_gpu-'):
                    raise RuntimeError('CUDA inference requires an onnxruntime-gpu wheel.')
                if cpu_version or gpu_version:
                    previous = 'onnxruntime' if cpu_version else 'onnxruntime-gpu'
                    subprocess.check_call([sys.executable, '-m', 'pip',
                                           'uninstall', '-y', previous])
                run_pip(f'install "{wheels[0]}"', 'Tagger ONNX runtime')

    import onnxruntime
    if wants_cuda and 'CUDAExecutionProvider' in onnxruntime.get_available_providers() \
            and hasattr(onnxruntime, 'preload_dlls'):
        onnxruntime.preload_dlls()
    available = onnxruntime.get_available_providers()
    if wants_cuda and 'CUDAExecutionProvider' in available:
        onnxrt_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    else:
        onnxrt_providers = ['CPUExecutionProvider']
        if wants_cuda:
            print(f'[Tagger] CUDAExecutionProvider unavailable ({available}); using CPU. '
                  'Install a CUDA-matched onnxruntime-gpu in Forge Python and restart.')
    return onnxruntime


def download_model_file(repo_id, filename, cache_dir, endpoint=None, revision=None):
    """Use the cached file without contacting the Hub; download only if absent."""
    kwargs = dict(repo_id=repo_id, filename=filename,
                  cache_dir=cache_dir, endpoint=endpoint, revision=revision)
    try:
        path = hf_hub_download(**kwargs, local_files_only=True)
    except LocalEntryNotFoundError:
        print(f'[Tagger] Cache miss: {repo_id}/{filename}; downloading to {cache_dir}')
        return hf_hub_download(**kwargs)
    print(f'[Tagger] Using local file: {path}')
    return path


class WaifuDiffusionInterrogator(Interrogator):
    """ Interrogator for Waifu Diffusion models """
    def __init__(
        self,
        name: str,
        model_path='model.onnx',
        tags_path='selected_tags.csv',
        repo_id=None,
    ) -> None:
        super().__init__(name)
        self.repo_id = repo_id
        self.model_path = model_path
        self.tags_path = tags_path

    def download(self) -> None:
        cache = getattr(shared.opts, 'tagger_hf_cache_dir', Its.hf_cache)
        mdir = Path(cache)
        print(f"Loading {self.name} model file from {self.repo_id}, "
              f"{self.model_path}")

        model_path = download_model_file(
            repo_id=self.repo_id,
            filename=self.model_path,
            cache_dir=cache,
            endpoint='https://hf-mirror.com'
        )
        tags_path = download_model_file(
            repo_id=self.repo_id,
            filename=self.tags_path,
            cache_dir=cache,
            endpoint='https://hf-mirror.com'
        )

        download_model = {
            'name': self.name,
            'model_path': model_path,
            'tags_path': tags_path,
        }
        mpath = Path(mdir, 'model.json')

        data = [download_model]

        if not os.path.exists(mdir):
            mdir.mkdir(parents=True, exist_ok=True)

        elif os.path.exists(mpath):
            with io.open(file=mpath, mode='r', encoding='utf-8') as filename:
                try:
                    data = json.load(filename)
                    # No need to append if it's already contained
                    if download_model not in data:
                        data.append(download_model)
                except json.JSONDecodeError as err:
                    print(f'Adding download_model {mpath} raised {repr(err)}')
                    data = [download_model]

        with io.open(mpath, 'w', encoding='utf-8') as filename:
            json.dump(data, filename)
        return model_path, tags_path

    def load(self) -> None:
        model_path, tags_path = self.download()
        ort = get_onnxrt()
        self.model = ort.InferenceSession(model_path,
                                          providers=onnxrt_providers)

        print(f'Loaded {self.name} model from {self.repo_id}')
        self.tags = read_csv(tags_path)

    def interrogate(
        self,
        image: Image
    ) -> Tuple[
        Dict[str, float],  # rating confidences
        Dict[str, float]  # tag confidences
    ]:
        # init model
        if self.model is None:
            self.load()

        # code for converting the image and running the model is taken from the
        # link below. thanks, SmilingWolf!
        # https://huggingface.co/spaces/SmilingWolf/wd-v1-4-tags/blob/main/app.py

        # convert an image to fit the model
        _, height, _, _ = self.model.get_inputs()[0].shape

        # alpha to white
        image = dbimutils.fill_transparent(image)

        image = asarray(image)
        # PIL RGB to OpenCV BGR
        image = image[:, :, ::-1]

        tags = dict

        image = dbimutils.make_square(image, height)
        image = dbimutils.smart_resize(image, height)
        image = image.astype(float32)
        image = expand_dims(image, 0)

        # evaluate model
        input_name = self.model.get_inputs()[0].name
        label_name = self.model.get_outputs()[0].name
        confidences = self.model.run([label_name], {input_name: image})[0]

        tags = self.tags[:][['name']]
        tags['confidences'] = confidences[0]

        # first 4 items are for rating (general, sensitive, questionable,
        # explicit)
        ratings = dict(tags[:4].values)

        # rest are regular tags
        tags = dict(tags[4:].values)

        return ratings, tags


class PixAIInterrogator(Interrogator):
    """PixAI mixed BF16 inference with the upstream PyTorch implementation."""

    repo_id = 'DraconicDragon/pixai-tagger-v1.0-mixed-bf16'
    # Pin the reviewed model code and weights to the same revision.
    revision = 'b7b4ce5b5d8e3c24a1171ff2b266e3345761eb0e'
    default_thresholds = {
        'general': 0.17, 'character': 0.27, 'style': 0.15,
        'copyright': 0.24, 'meta': 0.17, 'rating': 0.41,
    }

    def tag_categories(self):
        """Read category metadata even when predictions come from the cache."""
        if not hasattr(self, '_tag_categories'):
            cache = getattr(shared.opts, 'tagger_hf_cache_dir', Its.hf_cache)
            path = download_model_file(self.repo_id, 'config.json', cache,
                                       revision=self.revision)
            with open(path, encoding='utf-8') as file:
                config = json.load(file)
            categories = {}
            start = 0
            for category, count in config['tags_split']:
                for tag in config['tags'][start:start + count]:
                    categories[tag] = category
                start += count
            self._tag_categories = categories
        return self._tag_categories

    def load(self) -> None:
        import torch
        from safetensors.torch import load_file
        from transformers.modeling_utils import no_init_weights

        cache = getattr(shared.opts, 'tagger_hf_cache_dir', Its.hf_cache)
        paths = {
            filename: download_model_file(
                repo_id=self.repo_id, filename=filename, cache_dir=cache,
                revision=self.revision,
            )
            for filename in ('config.json', 'preprocessor_config.json',
                             'model.safetensors', 'tagger_pipeline.py')
        }
        # Execute only the pinned, reviewed upstream implementation.
        if not hasattr(self, '_pipeline'):
            spec = importlib.util.spec_from_file_location(
                'tagger_pixai_mixed_bf16', paths['tagger_pipeline.py'])
            pipeline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pipeline)
            self._pipeline = pipeline
        pipeline = self._pipeline
        with open(paths['config.json'], encoding='utf-8') as file:
            config = pipeline.ViTDetClsConfig(**json.load(file))
        with open(paths['preprocessor_config.json'], encoding='utf-8') as file:
            processor = pipeline.RescalePadProcessor(**json.load(file))

        with no_init_weights():
            model = pipeline.ViTDetCls(config)
        # assign=True preserves each saved tensor's dtype, including the FP32
        # head. A blanket model.bfloat16() or from_pretrained dtype would not.
        model.load_state_dict(load_file(paths['model.safetensors']), strict=True,
                              assign=True)
        device = torch.device('cpu')
        extra_device = shared.cmd_opts.additional_device_ids
        force_cpu = (extra_device.startswith('cpu:') if extra_device is not None
                     else use_cpu)
        if not force_cpu and torch.cuda.is_available():
            device_id = getattr(shared.cmd_opts, 'device_id', None)
            if extra_device is not None:
                device_id = extra_device.split(':')[1]
            device = torch.device('cuda' if device_id is None else f'cuda:{device_id}')
        model.to(device=device).eval()
        self.tags = config.tags
        self.tags_split = config.tags_split
        self.processor = processor
        # Publish last so download/load failures can be retried.
        self.model = model
        print(f'Loaded {self.name} model from {self.repo_id} on {device} '
              '(BF16 backbone, FP32 head)')

    def unload(self) -> bool:
        import torch

        device = next(self.model.parameters()).device if self.model is not None else None
        unloaded = super().unload()
        if unloaded and device.type == 'cuda':
            with torch.cuda.device(device):
                torch.cuda.empty_cache()
        return unloaded

    def interrogate(self, image: Image) -> Tuple[Dict[str, float], Dict[str, float]]:
        import torch

        if self.model is None:
            self.load()

        with torch.inference_mode(), torch.autocast(
                device_type=self.model.device.type, enabled=False):
            inputs = self.processor(image, return_tensors='pt')['pixel_values']
            inputs = inputs.to(device=self.model.device,
                               dtype=self.model.patch_embed.proj.weight.dtype)
            probabilities = self.model(inputs).float().sigmoid()[0].cpu().numpy()

        ratings, tags = {}, {}
        rating_names = {'rating:g': 'general', 'rating:s': 'sensitive',
                        'rating:q': 'questionable', 'rating:e': 'explicit'}
        start = 0
        for category, count in self.tags_split:
            for index in range(start, start + count):
                name = self.tags[index]
                confidence = float(probabilities[index])
                if category == 'rating':
                    ratings[rating_names[name]] = confidence
                else:
                    tags[name] = confidence
            start += count
        return ratings, tags

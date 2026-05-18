""" Interrogator class and subclasses for tagger """
import os
from pathlib import Path
import io
import json
from re import match as re_match
from platform import system
from typing import Tuple, Dict, Callable
from pandas import read_csv
from PIL import Image, UnidentifiedImageError
from numpy import asarray, float32, expand_dims
from tqdm import tqdm
from huggingface_hub import hf_hub_download

from modules import shared
from tagger import settings  # pylint: disable=import-error
from tagger.uiset import QData, IOData  # pylint: disable=import-error
from . import dbimutils  # pylint: disable=import-error # noqa

Its = settings.InterrogatorSettings

# select a device to process
use_cpu = ('all' in shared.cmd_opts.use_cpu) or (
    'interrogate' in shared.cmd_opts.use_cpu)

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
    odd_increment = 0

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

        for got in QData.in_db.values():
            QData.apply_filters(got)

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


# FIXME this is silly, in what scenario would the env change from MacOS to
# another OS? TODO: remove if the author does not respond.
def get_onnxrt():
    try:
        import onnxruntime
        return onnxruntime
    except ImportError:
        # only one of these packages should be installed at one time in an env
        # https://onnxruntime.ai/docs/get-started/with-python.html#install-onnx-runtime
        # TODO: remove old package when the environment changes?
        from launch import is_installed, run_pip
        if not is_installed('onnxruntime'):
            if system() == "Darwin":
                package_name = "onnxruntime-silicon"
            else:
                package_name = "onnxruntime-gpu"
            package = os.environ.get(
                'ONNXRUNTIME_PACKAGE',
                package_name
            )

            run_pip(f'install {package}', 'onnxruntime')

    import onnxruntime
    return onnxruntime


class WaifuDiffusionInterrogator(Interrogator):
    """ Interrogator for Waifu Diffusion models """
    def __init__(
        self,
        name: str,
        model_path='model.onnx',
        tags_path='selected_tags.csv',
        repo_id=None,
        is_hf=True,
    ) -> None:
        super().__init__(name)
        self.repo_id = repo_id
        self.model_path = model_path
        self.tags_path = tags_path
        self.tags = None
        self.model = None
        self.tags = None
        self.local_model = None
        self.local_tags = None
        self.is_hf = is_hf

    def download(self) -> None:
        mdir = Path(shared.models_path, 'interrogators')
        if self.is_hf:
            cache = getattr(shared.opts, 'tagger_hf_cache_dir', Its.hf_cache)
            print(f"Loading {self.name} model file from {self.repo_id}, "
                  f"{self.model_path}")

            model_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=self.model_path,
                cache_dir=cache,
                endpoint='https://hf-mirror.com'
                )
            tags_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=self.tags_path,
                cache_dir=cache,
                endpoint='https://hf-mirror.com'
                )
        else:
            model_path = self.local_model
            tags_path = self.local_tags

        download_model = {
            'name': self.name,
            'model_path': model_path,
            'tags_path': tags_path,
        }
        mpath = Path(mdir, 'model.json')

        data = [download_model]

        if not os.path.exists(mdir):
            os.mkdir(mdir)

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

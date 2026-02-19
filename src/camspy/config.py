from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path

import yaml
from schema import Schema, Optional

from camspy.resources import get_resource
from camspy.utils import get_abs

with open(get_resource('config_defaults.yaml')) as f:
    CONFIG_DEFAULTS = yaml.safe_load(f)


def config_schema() -> Schema:
    from schema import And, Or
    return Schema({
        'env_path': And(str, len),
        'device': {
            'name': And(str, len),
            'camera': Or('picam', 'arducam', 'usb', 'picam-direct'),
            'device_id': int,
            'frame_size': [int, int],
            'framerate': int,
            'init_delay': Or(float, int),
            'init_retry': Or(float, int),
            'arducam_registers': Or(None, And(str, len)),
            'max_error_rate': Or(float, int),
            'codec': Or('h264'),
            'annotation_scale': int,
            'flip_vertical': bool,
            'flip_horizontal': bool,
        },
        Optional('connection'): {
            'name': And(str, len),
            'host': And(str, len),
            'timeout': int,
        },
        Optional('sftp'): {
            'host': And(str, len),
            'port': And(str, len),
            'username': And(str, len),
            'password': And(str, len),
            'remote_dir': And(str, len),
        },
        Optional('mjpeg'): {
            'port': int,
            'stream_key': Or(None, And(str, len)),
        },
        Optional('recording'): {
            'output_directory': Or(None, And(str, len)),
            'max_video_file_size': Or(float, int),
            'bitrate': int,
            'data_bar': [Or(float, int), int],
            'show_fps': Or(None, bool),
        },
        Optional('processing'): {
            'mjpeg_stream': Or(None, bool),
            'record_video': Or(None, bool),
            'send_video': Or(None, bool),
        },
        Optional('logging'): {
            'level': Or('info', 'debug', 'INFO', 'DEBUG'),
            'filename': Or(None, And(str, len)),
            'log_dir': Or(None, And(str, len)),
            'log_stdout': Or(None, bool),
            'log_metrics': Or(None, bool),
            'log_extra_info': Or(None, bool),
            'ignore_warnings': Or(None, bool),
        }
    })


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}

    merged_cfg = merge_dict(CONFIG_DEFAULTS, cfg, True)
    _validate(merged_cfg)

    env_path = get_abs(Path(merged_cfg['env_path']))
    recording_dir = get_abs(Path(merged_cfg['recording']['output_directory']))

    merged_cfg['env_path'] = env_path.as_posix()
    merged_cfg['recording']['output_directory'] = recording_dir.as_posix()
    merged_cfg['recording']['name'] = merged_cfg['device']['name']
    merged_cfg['recording']['log_metrics'] = merged_cfg['logging']['log_metrics']
    return merged_cfg

    # path = merged_cfg['device']['arducam_registers']
    # if path is not None:
    #     path = os.path.abspath(path)
    #     if not os.path.exists(path):
    #         raise FileNotFoundError("Cannot find {} ".format(path))
    #     cfg['device']['arducam_registers'] = path


def _validate(raw_config: dict):
    from schema import SchemaError
    try:
        config_schema().validate(raw_config)
    except SchemaError as e:
        raise ConfigValidationError(e.code) from e


def merge_dict(d1, d2, immutable=False):
    """
    # Combine dictionaries recursively
    # preserving the originals
    # assumes d1 and d2 dictionaries!!
    :param d1: original dictionary
    :param d2: update dictionary
    :return:
    """

    d1 = {} if d1 is None else d1
    d2 = {} if d2 is None else d2
    d1 = deepcopy(d1) if immutable else d1

    for k in d2:
        # if d1 and d2 have dict for k, then recurse
        # else assign the new value to d1[k]
        if (k in d1 and isinstance(d1[k], Mapping)
                and isinstance(d2[k], Mapping)):
            merge_dict(d1[k], d2[k])
        else:
            d1[k] = d2[k]
    return d1


class ConfigValidationError(Exception):
    def __init__(self, message):
        super(ConfigValidationError, self).__init__(message)

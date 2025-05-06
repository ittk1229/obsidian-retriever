from pathlib import Path

import yaml

from obret.config.schema import BaseConfig


def load_yaml_config(file_path: str | Path) -> dict:
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def load_base_config(config_filepath: str | Path = "obret/config/base_config.yaml") -> BaseConfig:
    config_dict = load_yaml_config(config_filepath)
    return BaseConfig(**config_dict)

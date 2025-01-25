import yaml

from obret.config.schema import BaseConfig


def load_yaml_config(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def load_base_config() -> BaseConfig:
    config_dict = load_yaml_config("./obret/config/base_config.yaml")
    return BaseConfig(**config_dict)

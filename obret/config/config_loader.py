import os
from pathlib import Path

import yaml

from obret.config.schema import BaseConfig


def load_yaml_config(file_path: str | Path) -> dict:
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def load_base_config(config_filepath: str | Path = "obret/config/base_config.yaml") -> BaseConfig:
    config_dict = load_yaml_config(config_filepath)

    # Environment overrides (comma-separated for lists)
    if env_val := os.getenv("OBRET_EXCLUDE_DIRNAMES"):
        config_dict["exclude_dirnames"] = [
            name for name in (p.strip() for p in env_val.split(",")) if name
        ]
    if env_val := os.getenv("OBRET_REINDEX_INTERVAL"):
        try:
            config_dict["reindex_interval"] = int(env_val)
        except ValueError:
            pass
    if env_val := os.getenv("OBRET_SNIPPET_MAX_LEN"):
        try:
            config_dict["snippet_max_len"] = int(env_val)
        except ValueError:
            pass

    return BaseConfig(**config_dict)

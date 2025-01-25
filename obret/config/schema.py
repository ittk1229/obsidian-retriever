from pathlib import Path

from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    vault_dirpath: Path
    vault_dict_filepath: Path
    index_dirpath: str
    stopwords_filepath: Path
    exclude_dirnames: list[str]

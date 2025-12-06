from pathlib import Path

from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    vault_dirpath: Path
    index_dirpath: str
    stopwords_filepath: Path
    exclude_dirnames: list[str]
    reindex_interval: int = 600  # seconds
    snippet_max_len: int = 100  # 追加

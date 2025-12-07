from pathlib import Path

from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    vault_dirpath: Path
    index_dirpath: str
    stopwords_filepath: Path
    exclude_dirnames: list[str]
    reindex_interval: int = 600  # seconds
    snippet_max_len: int = 100  # snippet context (chars) on each side
    indexing_threads: int | None = None  # None = auto (cpu count)
    api_host: str = "127.0.0.1"
    api_port: int = 8000

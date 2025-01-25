from typing import Callable, Generator

import pyterrier as pt
from tqdm import tqdm

from obret.config.config_loader import load_base_config
from obret.utils.file_io import load_pickle
from obret.utils.tokenize import create_japanese_analyzer


def generate_notes(vault: dict, analyzer: Callable) -> Generator:
    for docno, note in tqdm(vault.items(), desc="Processing notes"):
        title = analyzer(note["title"])
        text = analyzer(note["text"])

        yield {
            "docno": docno,
            "title": title,
            "text": text,
        }


def main():
    base_config = load_base_config()

    # PyTerrier の初期化
    if not pt.java.started():
        pt.java.init()

    # インデックスの設定と作成
    indexer = pt.IterDictIndexer(
        base_config.index_dirpath,
        text_attrs=["title", "text"],
        fields=True,
        # TerrierIndexer parameter
        overwrite=True,
        tokeniser="UTFTokeniser",
    )

    # インデックス生成
    vault = load_pickle(base_config.vault_dict_filepath)
    analyzer = create_japanese_analyzer(base_config.stopword_filepath)
    index_ref = indexer.index(
        generate_notes(vault, analyzer),
    )
    index = pt.IndexFactory.of(index_ref)

    # 統計情報を表示
    print(index.getCollectionStatistics().toString())


if __name__ == "__main__":
    main()

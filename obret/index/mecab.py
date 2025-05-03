from pathlib import Path
from typing import Callable, Generator

import pyterrier as pt

from obret.config.config_loader import load_base_config
from obret.utils.note import ObsidianNote
from obret.utils.pt import create_japanese_analyzer


def generate_notes(
    vault_dirpath: str | Path, exclude_dirnames, analyzer: Callable
) -> Generator:
    vault_dirpath = Path(vault_dirpath)

    for i, note_filepath in enumerate(vault_dirpath.rglob("*.md")):
        if any(
            note_filepath.relative_to(vault_dirpath).parts[0] == dirname
            for dirname in exclude_dirnames
        ):
            continue

        note = ObsidianNote(vault_dirpath, note_filepath)

        docno = str(i)
        linkpath = str(note.relative_path)
        title_0 = note.title
        title = analyzer(note.title)
        body_0 = note.body
        body = analyzer(note.body)

        yield {
            "docno": docno,  # ちゃんとidにしたい
            "linkpath": linkpath,
            "title": title,
            "body": body,
            "title_0": title_0,
            "body_0": body_0,
        }


def main():
    base_config = load_base_config()

    # PyTerrier の初期化
    if not pt.java.started():
        pt.java.init()

    # インデックスの設定と作成
    indexer = pt.IterDictIndexer(
        str(Path(base_config.index_dirpath).resolve()),
        meta={"docno": 8, "linkpath": 128, "title_0": 128, "body_0": 1024},
        text_attrs=["title", "body"],
        fields=True,
        # TerrierIndexer parameter
        overwrite=True,
        verbose=True,
        tokeniser="UTFTokeniser",
    )

    # インデックス生成
    analyzer = create_japanese_analyzer(base_config.stopwords_filepath)
    index_ref = indexer.index(
        generate_notes(
            base_config.vault_dirpath, base_config.exclude_dirnames, analyzer
        ),
    )
    index = pt.IndexFactory.of(index_ref)

    # 統計情報を表示
    print(index.getCollectionStatistics().toString())


if __name__ == "__main__":
    main()

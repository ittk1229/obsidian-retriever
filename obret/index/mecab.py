from pathlib import Path
from typing import Callable, Generator

import pyterrier as pt

from obret.config.config_loader import load_base_config
from obret.config.schema import BaseConfig
from obret.utils.note import ObsidianNote
from obret.utils.pyterrier_utils import create_japanese_analyzer, create_md_parser


def generate_notes(
    vault_dirpath: str | Path, exclude_dirnames, analyzer: Callable, md_parser
) -> Generator:
    vault_dirpath = Path(vault_dirpath)

    for i, note_filepath in enumerate(vault_dirpath.rglob("*.md")):
        if any(
            note_filepath.relative_to(vault_dirpath).parts[0] == dirname
            for dirname in exclude_dirnames
        ):
            continue

        note = ObsidianNote(vault_dirpath, note_filepath)
        # frontmatterの値も検索に利用
        frontmatter_values = (
            " ".join(map(str, note.frontmatter.values())) if note.frontmatter else ""
        )

        # 検索に用いるフィールド
        docno = str(i)
        title = analyzer(note.title)
        body = analyzer(note.body + " " + frontmatter_values)
        # メタデータとして保存するフィールド
        linkpath = str(note.relative_path)
        title_0 = note.title
        body_0 = md_parser(note.body)

        yield {
            "docno": docno,
            "title": title,
            "body": body,
            "linkpath": linkpath,
            "title_0": title_0,
            "body_0": body_0,
        }


def build_index_from_notes(cfg: BaseConfig):
    # インデックスの設定と作成
    indexer = pt.IterDictIndexer(
        str(Path(cfg.index_dirpath).resolve()),
        meta={"docno": 8, "linkpath": 128, "title_0": 128, "body_0": 1024},
        text_attrs=["title", "body"],
        fields=True,
        # TerrierIndexer parameter
        overwrite=True,
        verbose=True,
        tokeniser="UTFTokeniser",
    )

    # インデックス生成
    analyzer = create_japanese_analyzer(cfg.stopwords_filepath)
    md_parser = create_md_parser()
    index_ref = indexer.index(
        generate_notes(cfg.vault_dirpath, cfg.exclude_dirnames, analyzer, md_parser),
    )
    index = pt.IndexFactory.of(index_ref)

    # 統計情報を表示
    print(index.getCollectionStatistics().toString())

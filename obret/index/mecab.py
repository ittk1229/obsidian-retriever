import os
from pathlib import Path
from typing import Callable, Generator

import pyterrier as pt

from obret.config.config_loader import load_base_config
from obret.config.schema import BaseConfig
from obret.utils.note import ObsidianNote
from obret.utils.pyterrier_utils import create_japanese_analyzer, create_md_parser


def generate_notes(
    vault_dirpath: str | Path,
    exclude_dirnames,
    analyzer: Callable,
    md_parser: Callable,
) -> Generator:
    vault_dirpath = Path(vault_dirpath)

    print(f"Indexing notes under: {vault_dirpath}")
    for i, note_filepath in enumerate(vault_dirpath.rglob("*.md")):
        rel_parts = note_filepath.relative_to(vault_dirpath).parts
        # skip if the first directory matches an excluded folder
        if rel_parts and rel_parts[0] in exclude_dirnames:
            continue
        if i % 500 == 0 and i > 0:
            print(f"  processed {i} notes... latest={note_filepath}")

        note = ObsidianNote(vault_dirpath, note_filepath)
        frontmatter_values = (
            " ".join(map(str, note.frontmatter.values())) if note.frontmatter else ""
        )
        docno = str(i)
        title = analyzer(note.title)
        body = analyzer(note.body + " " + frontmatter_values)
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


def build_index_from_notes(cfg: BaseConfig, target_dirpath: str | Path | None = None):
    index_dir = Path(target_dirpath) if target_dirpath else Path(cfg.index_dirpath)
    # インデックスの設定と作成
    threads = cfg.indexing_threads or (os.cpu_count() or 1)
    indexer = pt.IterDictIndexer(
        str(index_dir.resolve()),
        meta={"docno": 8, "linkpath": 128, "title_0": 128, "body_0": 1024},
        text_attrs=["title", "body"],
        fields=True,
        # TerrierIndexer parameter
        overwrite=True,
        verbose=True,
        tokeniser="UTFTokeniser",
        threads=threads,
    )

    # インデックス生成
    analyzer = create_japanese_analyzer(cfg.stopwords_filepath)
    md_parser = create_md_parser()
    index_ref = indexer.index(
        generate_notes(cfg.vault_dirpath, cfg.exclude_dirnames, analyzer, md_parser),
    )
    index = pt.IndexFactory.of(index_ref)

    # 統計情報を表示
    print("Index built.")
    print(index.getCollectionStatistics().toString())

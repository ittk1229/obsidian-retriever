import os
from pathlib import Path
from typing import Callable, Generator, Iterable

import pyterrier as pt

from obret.config.config_loader import load_base_config
from obret.config.schema import BaseConfig
from obret.utils.note import ObsidianNote
from obret.utils.pyterrier_utils import create_japanese_analyzer, create_md_parser


def generate_notes(
    filepaths: Iterable[Path],
    vault_dirpath: str | Path,
    analyzer: Callable,
    md_parser: Callable,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Generator:
    vault_dirpath = Path(vault_dirpath)
    total = None
    try:
        total = len(filepaths)  # type: ignore[arg-type]
    except Exception:
        pass

    for i, note_filepath in enumerate(filepaths):
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
        if progress_callback and total:
            progress_callback(i + 1, total)


def build_index_from_notes(
    cfg: BaseConfig,
    target_dirpath: str | Path | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
):
    index_dir = Path(target_dirpath) if target_dirpath else Path(cfg.index_dirpath)
    vault_dirpath = Path(cfg.vault_dirpath)

    # 対象ファイルの事前収集で総数を把握
    filepaths = []
    for note_filepath in vault_dirpath.rglob("*.md"):
        rel_parts = note_filepath.relative_to(vault_dirpath).parts
        if rel_parts and rel_parts[0] in cfg.exclude_dirnames:
            continue
        filepaths.append(note_filepath)

    total_notes = len(filepaths)
    print(f"Indexing notes under: {vault_dirpath} (total: {total_notes})")

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
        generate_notes(
            filepaths, cfg.vault_dirpath, analyzer, md_parser, progress_callback
        ),
    )
    index = pt.IndexFactory.of(index_ref)

    # 統計情報を表示
    print("Index built.")
    print(index.getCollectionStatistics().toString())

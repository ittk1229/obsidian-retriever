import argparse
import asyncio
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import pyterrier as pt
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from obret.api.router import router
from obret.config.config_loader import load_base_config
from obret.index.mecab import build_index_from_notes
from obret.retrieve.bm25 import build_pipeline
from obret.utils.pyterrier_utils import create_japanese_analyzer, index_ready


@asynccontextmanager
async def lifespan(app: FastAPI, config_path: Optional[str]):
    cfg = load_base_config(config_path) if config_path else load_base_config()

    # PyTerrier の初期化
    if not pt.java.started():
        pt.java.init()

    # 検索パイププラインの初期化
    index_path = str(Path(cfg.index_dirpath).resolve())
    if not index_ready(index_path):
        build_index_from_notes(cfg)

    try:
        index = pt.IndexFactory.of(index_path)
    except Exception:
        # Rebuild once in case an empty/corrupted index directory exists
        build_index_from_notes(cfg)
        index = pt.IndexFactory.of(index_path)
    analyzer = create_japanese_analyzer(cfg.stopwords_filepath)
    pipeline = build_pipeline(index, analyzer)

    # アプリケーションの状態に設定を保存
    app.state.config = cfg
    app.state.index = index
    app.state.analyzer = analyzer
    app.state.pipeline = pipeline
    app.state.reindex_lock = asyncio.Lock()
    app.state.rebuild_index = lambda reason="manual": rebuild_index(app, reason)
    app.state.loop = asyncio.get_running_loop()
    app.state.reindexing = False
    app.state.reindex_progress = None

    # 自動再インデックスのためのタスク開始
    app.state.reindex_task = asyncio.create_task(periodic_reindex(app))

    yield

    # アプリ終了時にタスクをキャンセル
    app.state.reindex_task.cancel()
    try:
        await app.state.reindex_task
    except asyncio.CancelledError:
        pass


async def periodic_reindex(app: FastAPI):
    """定期的にインデックスを再構築するバックグラウンドタスク"""
    while True:
        try:
            await asyncio.sleep(app.state.config.reindex_interval)
            await rebuild_index(app, reason="auto")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error during auto-reindexing: {e}")


async def rebuild_index(app: FastAPI, reason: str = "manual"):
    async with app.state.reindex_lock:
        app.state.reindexing = True
        app.state.reindex_progress = 0.0
        cfg = app.state.config
        base_dir = Path(cfg.index_dirpath).resolve()
        temp_dir = base_dir.with_name(base_dir.name + ".tmp")
        backup_dir = base_dir.with_name(base_dir.name + ".old")

        def _build_and_swap():
            print(f"{reason.capitalize()} reindex: preparing temp index at {temp_dir}")
            temp_dir.parent.mkdir(parents=True, exist_ok=True)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if backup_dir.exists():
                shutil.rmtree(backup_dir)

            def _progress(done: int, total: int):
                if total <= 0:
                    app.state.reindex_progress = 100.0
                else:
                    app.state.reindex_progress = min(100.0, (done / total) * 100.0)

            build_index_from_notes(cfg, target_dirpath=temp_dir, progress_callback=_progress)

            if base_dir.exists():
                base_dir.rename(backup_dir)
            temp_dir.rename(base_dir)

            index = pt.IndexFactory.of(str(base_dir))
            pipeline = build_pipeline(index, app.state.analyzer)
            print(
                f"{reason.capitalize()} reindex: swap completed (old backup={backup_dir})"
            )
            return index, pipeline

        try:
            index, pipeline = await asyncio.to_thread(_build_and_swap)
            app.state.index = index
            app.state.pipeline = pipeline
        finally:
            app.state.reindexing = False
            app.state.reindex_progress = None


def create_app(config_path: Optional[str] = None):
    app = FastAPI(lifespan=lambda app: lifespan(app, config_path))

    # CORS（Obsidian プラグインからのアクセスを許可）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 必要に応じて制限してもOK
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ルーターを追加
    app.include_router(router)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Obsidian Retriever API server"
    )
    parser.add_argument(
        "--config", "-c", type=str, help="Path to the configuration file"
    )
    args = parser.parse_args()

    app = create_app(args.config)
    uvicorn.run(app, host="0.0.0.0", port=8229, log_level="debug")

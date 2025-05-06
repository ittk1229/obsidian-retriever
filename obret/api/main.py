import argparse
import asyncio
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
from obret.utils.pyterrier_utils import create_japanese_analyzer


@asynccontextmanager
async def lifespan(app: FastAPI, config_path: Optional[str]):
    cfg = load_base_config(config_path) if config_path else load_base_config()

    # PyTerrier の初期化
    if not pt.java.started():
        pt.java.init()

    # 検索パイププラインの初期化
    if not Path(cfg.index_dirpath).exists():
        build_index_from_notes(cfg)

    index = pt.IndexFactory.of(cfg.index_dirpath)
    analyzer = create_japanese_analyzer(cfg.stopwords_filepath)
    pipeline = build_pipeline(index, analyzer)

    # アプリケーションの状態に設定を保存
    app.state.config = cfg
    app.state.index = index
    app.state.analyzer = analyzer
    app.state.pipeline = pipeline

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

            # インデックスの再構築
            print("Auto-reindexing started...")
            build_index_from_notes(app.state.config)
            index = pt.IndexFactory.of(app.state.config.index_dirpath)

            # 検索パイプラインの再構築
            pipeline = build_pipeline(index, app.state.analyzer)

            app.state.index = index
            app.state.pipeline = pipeline

            print("Auto-reindexing completed")
        except Exception as e:
            print(f"Error during auto-reindexing: {e}")


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
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

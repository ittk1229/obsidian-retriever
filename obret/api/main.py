import asyncio
import datetime
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pyterrier as pt
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from obret.config.config_loader import load_base_config
from obret.config.schema import BaseConfig
from obret.index.mecab import build_index_from_notes
from obret.retrieve.bm25 import build_pipeline
from obret.utils.pyterrier_utils import create_japanese_analyzer, df_to_dict_list


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg: BaseConfig = load_base_config()

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
            analyzer = create_japanese_analyzer(app.state.config.stopwords_filepath)
            pipeline = build_pipeline(index, analyzer)

            app.state.index = index
            app.state.pipeline = pipeline

            print("Auto-reindexing completed")
        except Exception as e:
            print(f"Error during auto-reindexing: {e}")


app = FastAPI(lifespan=lifespan)
# CORS（Obsidian プラグインからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて制限してもOK
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# api
@app.get("/search")
def search(q: str = Query(..., description="Search query")):
    result_df = app.state.pipeline.search(q)
    result = df_to_dict_list(result_df)
    return {"results": result}


@app.post("/index")
def rebuild_index(background_tasks: BackgroundTasks):
    # バックグラウンドタスクとしてインデックスの再構築を実行
    background_tasks.add_task(rebuild_index_task, app)
    return {"message": "Index rebuild started in background"}


def rebuild_index_task(app: FastAPI):
    """明示的なインデックス再構築のバックグラウンドタスク"""
    try:
        # インデックスの再構築
        build_index_from_notes(app.state.config)
        index = pt.IndexFactory.of(app.state.config.index_dirpath)

        # 検索パイプラインの再構築
        analyzer = create_japanese_analyzer(app.state.config.stopwords_filepath)
        pipeline = build_pipeline(index, analyzer)

        app.state.index = index
        app.state.pipeline = pipeline

        print("Manual index rebuild completed")
    except Exception as e:
        print(f"Error during manual index rebuild: {e}")


@app.get("/index/status")
def index_status():
    # インデックスの状態を取得
    last_indexed = os.path.getmtime(app.state.config.index_dirpath)
    # 読みやすい形式に変換
    last_indexed = datetime.datetime.fromtimestamp(last_indexed).strftime("%m/%d %H:%M")
    note_count = app.state.index.getCollectionStatistics().getNumberOfDocuments()

    return {
        "last_indexed": last_indexed,
        "note_count": note_count,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

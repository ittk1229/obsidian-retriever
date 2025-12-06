import datetime
import os

import pyterrier as pt
from fastapi import APIRouter, BackgroundTasks, Query, Request

from obret.index.mecab import build_index_from_notes
from obret.retrieve.bm25 import build_pipeline
from obret.utils.pyterrier_utils import df_to_dict_list

router = APIRouter()


@router.get("/search")
def search(request: Request, q: str = Query(..., description="Search query")):
    result_df = request.app.state.pipeline.search(q)
    result = df_to_dict_list(result_df, snippet_maxlen=request.app.state.config.snippet_max_len)
    return {"results": result}


@router.post("/index")
def rebuild_index(background_tasks: BackgroundTasks, request: Request):
    # バックグラウンドタスクとしてインデックスの再構築を実行
    background_tasks.add_task(rebuild_index_task, request.app)
    return {"message": "Index rebuild started in background"}


@router.get("/index/status")
def index_status(request: Request):
    # インデックスの状態を取得
    last_indexed = os.path.getmtime(request.app.state.config.index_dirpath)
    # 読みやすい形式に変換
    last_indexed = datetime.datetime.fromtimestamp(last_indexed).strftime("%m/%d %H:%M")
    note_count = (
        request.app.state.index.getCollectionStatistics().getNumberOfDocuments()
    )

    return {
        "last_indexed": last_indexed,
        "note_count": note_count,
    }


def rebuild_index_task(app):
    """明示的なインデックス再構築のバックグラウンドタスク"""
    try:
        # インデックスの再構築
        build_index_from_notes(app.state.config)
        index = pt.IndexFactory.of(app.state.config.index_dirpath)

        pipeline = build_pipeline(index, app.state.analyzer)

        app.state.index = index
        app.state.pipeline = pipeline

        print("Manual index rebuild completed")
    except Exception as e:
        print(f"Error during manual index rebuild: {e}")

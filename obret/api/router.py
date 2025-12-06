import asyncio
import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Query, Request

from obret.utils.pyterrier_utils import df_to_dict_list

router = APIRouter()


@router.get("/search")
def search(request: Request, q: str = Query(..., description="Search query")):
    result_df = request.app.state.pipeline.search(q)
    result = df_to_dict_list(
        result_df,
        snippet_maxlen=request.app.state.config.snippet_max_len,
        vault_dirpath=request.app.state.config.vault_dirpath,
        query=q,
    )
    return {"results": result}


@router.post("/index")
def rebuild_index(background_tasks: BackgroundTasks, request: Request):
    # バックグラウンドタスクとしてインデックスの再構築を実行
    background_tasks.add_task(schedule_rebuild, request.app)
    return {"message": "Index rebuild started in background"}


@router.get("/index/status")
def index_status(request: Request):
    # インデックスの状態を取得
    index_path = Path(request.app.state.config.index_dirpath).resolve()
    last_indexed = index_path.stat().st_mtime
    # 読みやすい形式に変換
    last_indexed = datetime.datetime.fromtimestamp(last_indexed).strftime("%m/%d %H:%M")
    note_count = (
        request.app.state.index.getCollectionStatistics().getNumberOfDocuments()
    )

    return {
        "last_indexed": last_indexed,
        "note_count": note_count,
    }


def schedule_rebuild(app):
    """明示的なインデックス再構築のバックグラウンドタスク"""
    try:
        loop = app.state.loop
        asyncio.run_coroutine_threadsafe(app.state.rebuild_index("manual"), loop)
    except Exception as e:
        print(f"Error scheduling manual index rebuild: {e}")

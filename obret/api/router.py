import asyncio
import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from pydantic import BaseModel, Field

from obret.utils.pyterrier_utils import df_to_dict_list

router = APIRouter()


class ConfigUpdate(BaseModel):
    exclude_dirnames: list[str] | None = None
    reindex_interval: int | None = Field(None, gt=0, description="seconds")
    snippet_max_len: int | None = Field(None, gt=0, description="chars of context each side")


@router.get("/search")
def search(request: Request, q: str = Query(..., description="Search query")):
    # Block only during the brief swap window to keep queries available while building
    if getattr(request.app.state, "swap_in_progress", False):
        raise HTTPException(status_code=503, detail="Reindexing in progress")
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


@router.get("/config")
def get_config(request: Request):
    cfg = request.app.state.config
    return {
        "exclude_dirnames": cfg.exclude_dirnames,
        "reindex_interval": cfg.reindex_interval,
        "snippet_max_len": cfg.snippet_max_len,
        "api_host": cfg.api_host,
        "api_port": cfg.api_port,
    }


@router.patch("/config")
def update_config(request: Request, payload: ConfigUpdate):
    cfg = request.app.state.config
    updated = {}

    if payload.exclude_dirnames is not None:
        cfg.exclude_dirnames = payload.exclude_dirnames
        updated["exclude_dirnames"] = cfg.exclude_dirnames

    if payload.reindex_interval is not None:
        cfg.reindex_interval = payload.reindex_interval
        updated["reindex_interval"] = cfg.reindex_interval

    if payload.snippet_max_len is not None:
        cfg.snippet_max_len = payload.snippet_max_len
        updated["snippet_max_len"] = cfg.snippet_max_len

    return {"updated": updated, "reindexing": bool(getattr(request.app.state, "reindexing", False))}


@router.get("/index/status")
def index_status(request: Request):
    # インデックスの状態を取得（起動直後やエラー時に None の場合があるので防御的に扱う）
    index_path = Path(request.app.state.config.index_dirpath).resolve()
    try:
        last_indexed_ts = index_path.stat().st_mtime
        last_indexed = datetime.datetime.fromtimestamp(last_indexed_ts).strftime("%m/%d %H:%M")
    except (FileNotFoundError, OSError):
        last_indexed = None

    note_count = None
    idx = getattr(request.app.state, "index", None)
    if idx:
        try:
            note_count = idx.getCollectionStatistics().getNumberOfDocuments()
        except Exception:
            note_count = None

    return {
        "last_indexed": last_indexed,
        "note_count": note_count,
        "reindexing": bool(getattr(request.app.state, "reindexing", False)),
        "reindex_progress": getattr(request.app.state, "reindex_progress", None),
    }


def schedule_rebuild(app):
    """明示的なインデックス再構築のバックグラウンドタスク"""
    try:
        loop = getattr(app.state, "loop", None)
        if loop is None or loop.is_closed():
            print("Event loop is closed; skip manual index rebuild request.")
            return
        asyncio.run_coroutine_threadsafe(app.state.rebuild_index("manual"), loop)
    except Exception as e:
        print(f"Error scheduling manual index rebuild: {e}")

import pyterrier as pt
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from obret.config.config_loader import load_base_config
from obret.config.schema import BaseConfig
from obret.utils.pt import create_japanese_analyzer, df_to_dict_list

app = FastAPI()

# CORS（Obsidian プラグインからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて制限してもOK
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 検索モデルの定義
base_config: BaseConfig = load_base_config()

if not pt.java.started():
    pt.java.init()

index = pt.IndexFactory.of(base_config.index_dirpath)
print(index.getCollectionStatistics().getNumberOfDocuments())

query_analyzer = create_japanese_analyzer(base_config.stopwords_filepath)

pipeline = (
    pt.apply.query(lambda row: query_analyzer(row.query))
    >> pt.terrier.Retriever(
        index, wmodel="BM25F", controls={"w.0": 2, "w.1": 1, "c.0": 0.5, "c.1": 0.75}
    )
    % 20
    >> pt.text.get_text(index)
)


@app.get("/")
def mock_search(q: str = Query(..., description="Search query")):
    mock_results = [
        {
            "title": "Obsidian",
            "linkpath": "Obsidian",
            "snippet": "Snippet from Note titled 'Obsidian'. (by api)",
        },
        {
            "title": "Obsidian Web Clipper",
            "linkpath": "Obsidian Web Clipper",
            "snippet": "Snippet from Note titled 'Obsidian Web Clipper'. (by api)",
        },
    ]
    return {"results": mock_results}


@app.get("/search")
def search(q: str = Query(..., description="Search query")):
    print(f"Received search query (/search): {q}")
    result_df = pipeline.search(q)
    print(result_df)
    result = df_to_dict_list(result_df)
    return {"results": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")

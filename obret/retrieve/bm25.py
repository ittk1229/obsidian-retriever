from pathlib import Path

import pyterrier as pt

from obret.config.config_loader import load_base_config
from obret.config.schema import BaseConfig
from obret.utils.pt import create_japanese_analyzer, df_to_dict_list


def main(query: str = "obsidian"):
    base_config: BaseConfig = load_base_config()

    if not pt.java.started():
        pt.java.init()

    index = pt.IndexFactory.of(base_config.index_dirpath)
    print(index.getCollectionStatistics().getNumberOfDocuments())

    query_analyzer = create_japanese_analyzer(base_config.stopwords_filepath)

    pipeline = (
        pt.apply.query(lambda row: query_analyzer(row.query))
        >> pt.terrier.Retriever(index, wmodel="BM25") % 20
        >> pt.text.get_text(index)
    )

    result = pipeline.search(query)
    result = df_to_dict_list(result)
    print(result)


if __name__ == "__main__":
    main()

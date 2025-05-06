import pyterrier as pt


# タイトル:本文 = 2:1 の重み付けをしたBM25F
def build_pipeline(index, analyzer):
    pipeline = (
        pt.apply.query(lambda row: analyzer(row.query))
        >> pt.terrier.Retriever(
            index,
            wmodel="BM25F",
            controls={"w.0": 2, "w.1": 1},
        )
        % 10
        >> pt.text.get_text(index)
    )
    return pipeline

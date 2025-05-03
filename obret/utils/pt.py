import re

from fugashi import Tagger

STOP_SYMBOLS = "[!\"#$%&'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]"


def create_japanese_analyzer(stopword_filepath):
    stopword_regex = re.compile(STOP_SYMBOLS)
    stopwords = set([w.strip() for w in open(stopword_filepath).readlines()])
    tagger = Tagger()

    def _japanese_analyzer(text):
        text = stopword_regex.sub("", text)
        surfaces = []
        for node in tagger(text):
            word = node.feature.orthBase if node.feature.orthBase else node.surface
            if word not in stopwords:
                surfaces.append(word)
        result = " ".join(surfaces)
        return result

    return _japanese_analyzer


def df_to_dict_list(df, snippet_maxlen=100):
    result = []
    for _, row in df.iterrows():
        snippet = row["body_0"]
        if len(snippet) > snippet_maxlen:
            snippet = snippet[:snippet_maxlen] + "..."
        result.append(
            {"title": row["title_0"], "linkpath": row["linkpath"], "snippet": snippet}
        )
    return result

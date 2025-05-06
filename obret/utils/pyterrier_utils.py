import re

import mistune
from bs4 import BeautifulSoup as bs
from fugashi import Tagger

STOP_SYMBOLS = "[!\"#$%&'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]"


# 日本語の形態素解析器
def create_japanese_analyzer(stopword_filepath):
    stopword_regex = re.compile(STOP_SYMBOLS)
    stopwords = set([w.strip() for w in open(stopword_filepath).readlines()])
    tagger = Tagger()

    def _japanese_analyzer(text):
        text = stopword_regex.sub(" ", text)
        surfaces = []
        for node in tagger(text):
            word = node.feature.orthBase if node.feature.orthBase else node.surface
            if word not in stopwords:
                surfaces.append(word)
        result = " ".join(surfaces)
        return result

    return _japanese_analyzer


# そのうちmistuneで実装したい
def replace_wikilink(match):
    link = match.group(1)  # [[東京]] の「東京」、[[東京|Tokyo]] の「東京」
    alias = match.group(2)  # [[東京|Tokyo]] の「Tokyo」、なければ None
    return alias if alias else link


def get_plaintext(html) -> str:
    soup = bs(html, "html.parser")
    # HTML タグを除去してテキストを取得
    text = soup.get_text()
    # テキストを整形
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\$\$", "", text)
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", replace_wikilink, text)
    return text.strip()


# MarkdownをHTMLに変換するための関数
def create_md_parser():
    # Markdownのパーサーを作成
    markdown = mistune.create_markdown(
        escape=False,
        hard_wrap=True,
        plugins=["strikethrough", "table", "task_lists", "math"],
    )
    return lambda text: get_plaintext(markdown(text))


# PyTerrierの検索結果をAPIのレスポンス形式に変換
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

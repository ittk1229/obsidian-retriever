import re
from pathlib import Path

import mistune
from bs4 import BeautifulSoup as bs
from fugashi import Tagger

STOP_SYMBOLS = "[!\"#$%&'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]"


def index_ready(index_dirpath: str | Path) -> bool:
    """
    Returns True when a Terrier index looks usable.
    Checks for the standard data.properties file rather than just directory existence.
    """
    index_dir = Path(index_dirpath)
    if not index_dir.is_dir():
        return False

    data_props = index_dir / "data.properties"
    # Some environments mount the path differently; resolve before checking to avoid false negatives.
    if data_props.exists():
        return True

    # Fall back to a generic check so we rebuild empty directories tracked in the repo.
    try:
        return any(index_dir.iterdir())
    except OSError:
        return False


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


FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n^---\s*\n", re.DOTALL | re.MULTILINE)


def strip_frontmatter(text: str) -> str:
    """Remove the leading frontmatter block if present."""
    return FRONTMATTER_REGEX.sub("", text, count=1)


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
def df_to_dict_list(
    df,
    snippet_maxlen=100,
    vault_dirpath: Path | str | None = None,
    query: str | None = None,
):
    result = []
    for _, row in df.iterrows():
        snippet = None
        if vault_dirpath and query:
            snippet = build_snippet_from_file(
                row["linkpath"], vault_dirpath, query, context_chars=snippet_maxlen
            )

        if not snippet:
            snippet = row["body_0"]
            if len(snippet) > snippet_maxlen:
                snippet = snippet[:snippet_maxlen] + "..."
        result.append(
            {"title": row["title_0"], "linkpath": row["linkpath"], "snippet": snippet}
        )
    return result


def build_snippet_from_file(linkpath: str, vault_dirpath: Path | str, query: str, context_chars: int = 100):
    """
    ファイル本体を読み取り、クエリにマッチした箇所の前後 context_chars 文字でスニペットを生成する。
    クエリが見つからない場合は先頭から context_chars*2 を返す。
    """
    terms = [t for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return None

    try:
        fullpath = Path(vault_dirpath) / linkpath
        text = fullpath.read_text(encoding="utf-8")
        text = strip_frontmatter(text)
    except Exception:
        return None

    md_parser = create_md_parser()
    plain = md_parser(text).strip()
    if not plain:
        return None

    match_span = None
    for term in terms:
        m = re.search(re.escape(term), plain)
        if m:
            match_span = m.span()
            break

    if match_span:
        start, end = match_span
        snippet_start = max(0, start - context_chars)
        snippet_end = min(len(plain), end + context_chars)
    else:
        snippet_start = 0
        snippet_end = min(len(plain), context_chars * 2)

    snippet = plain[snippet_start:snippet_end]
    prefix = "..." if snippet_start > 0 else ""
    suffix = "..." if snippet_end < len(plain) else ""
    return f"{prefix}{snippet}{suffix}"

import re
from pathlib import Path

import yaml


class ObsidianNote:
    def __init__(self, vault_dirpath: str | Path, note_filepath: str | Path):
        self.vault_path = Path(vault_dirpath).resolve()
        self.note_path = Path(note_filepath).resolve()

        if not self.note_path.is_file():
            raise FileNotFoundError(f"Note file not found: {self.note_path}")

        # 相対パス（vaultからの相対パス）
        self.relative_path = self.note_path.relative_to(self.vault_path)

        # ファイル内容の読み込み
        with open(self.note_path, "r", encoding="utf-8") as f:
            text = f.read()

        # frontmatter と body を分割して格納
        self.frontmatter = {}
        self.body = ""
        self._parse_content(text)
        self.title = self.get_title()

    def _parse_content(self, text: str):
        # frontmatter 部分を正規表現で抽出
        frontmatter_pattern = r"^---\s*\n(.*?)\n^---\s*\n"
        match = re.search(frontmatter_pattern, text, re.DOTALL | re.MULTILINE)

        if match:
            # YAMLのパース
            self.frontmatter = yaml.safe_load(match.group(1)) or {}
            # frontmatter 部分を削除
            text = text[match.end() :]

        # 本文は残り部分
        self.body = text.strip()

    def get_title(self) -> str:
        # frontmatter に title がない場合はファイル名をタイトルとする
        title = self.frontmatter.get("title", None)
        if not title:
            title = self.note_path.stem
        return title

# Obsidian Retriever

Obsidian Retriever は、Obsidian Vault 用の検索エンジンです。

Obsidian SERP 経由で、Obsidian アプリ経由で利用することができます。

現在は Obsidian がインストールされた PC での実行を想定しており、BM25 を用いた効率的な単語一致検索のみを提供しています。

## 特徴

- **日本語検索**: MeCab を使用して適切な日本語のトークナイズを実現
- **BM25F ランキング**: タイトル:本文 = 2:1 の重み付けで BM25F アルゴリズムを実装
- **自動再インデックス**: 定期的にインデックスを再構築して検索結果を最新の状態に保持
- **REST API**: Obsidian プラグインをはじめとする外部ツールと連携するためのシンプルな API
- **PyTerrier**: PyTerrier を利用したカスタマイズ性の高い検索機能を提供

## インストール

### 前提条件

- Python 3.8 以上
- UniDic 辞書を使用した MeCab
- Java 実行環境（PyTerrier に必要）

### 手順

```sh
# リポジトリをクローン
git clone https://github.com/ittk1229/obsidian-retriever

# uvがインストールされていない場合はインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係をインストール
uv sync

# MeCab用のUniDic辞書をダウンロード
uv run python -m unidic download
```

## 設定

`obret/config/base_config.yaml`にある設定ファイルを変更するか、新しい設定ファイルを作成します：

```yaml
vault_dirpath: /path/to/your/obsidian/vault
exclude_dirnames: # valt_dirpathからの相対パス、指定されなかった全てのフォルダからmdを探して処理
  - templates
reindex_interval: 600 # 秒
```

### 設定オプション

| オプション           | 説明                                             | デフォルト値            |
| -------------------- | ------------------------------------------------ | ----------------------- |
| `vault_dirpath`      | Obsidian ボールトへのパス                        | `path/to/your_vault`    |
| `index_dirpath`      | 検索インデックスが保存されるディレクトリ         | `./data/indexes/mecab/` |
| `stopwords_filepath` | ストップワードを含むファイルへのパス             | `./data/stopwords.txt`  |
| `exclude_dirnames`   | インデックス作成から除外するディレクトリのリスト | `['templates']`         |
| `reindex_interval`   | 自動再インデックスの間隔（秒）                   | `600`（10 分）          |

カスタム設定ファイル（例：`my_config.yaml`）を作成し、サーバー起動時に指定することもできます。

## 使用方法

### サーバーの起動

```sh
# デフォルト設定で起動
uv run obret/api/main.py

# カスタム設定で起動
uv run obret/api/main.py --config path/to/your/config.yaml
```

サーバーはデフォルトで`http://127.0.0.1:8000`で起動します。

### API エンドポイント

#### 検索

```
GET /search?q=${query}
```

クエリに一致する検索結果を返します。

レスポンス例：

```json
{
  "results": [
    {
      "title": "ノートのタイトル",
      "linkpath": "フォルダ/ノート.md",
      "snippet": "ノート内容の一部..."
    }
  ]
}
```

#### インデックスの状態

```
GET /index/status
```

現在のインデックスに関する情報を返します。

レスポンス例：

```json
{
  "last_indexed": "05/06 15:30",
  "note_count": 1250
}
```

#### インデックスの再構築

```
POST /index
```

検索インデックスの手動再構築をトリガーします。

レスポンス例：

```json
{
  "message": "Index rebuild started in background"
}
```

# investment-research-copilot

## 作業の進め方

- 変更したら `python -m pytest backend` を通す。
- 振る舞いを変えないリファクタリングでは、変更前の出力を先に記録し、変更後と比べる。
  - Claude に送る内容、検索結果、関数の中身（AST）など、比べられるものを比べる。
- 評価は Claude API を呼ぶので、`--limit 3` で確かめてから全件を実行する。
  - 比較の基準は `evaluation/results/mvp-baseline.json`。
- プロンプトの文言を変えたら、評価を実行し直して結果を比べる。リファクタリングのついでには変えない。

## コードの書き方

- `__init__.py` 以外のすべての `.py` の先頭に、モジュールの docstring を 1〜2 行書く。
  - このファイルに何が入っているかと、Claude API を呼ぶかどうかを書く。
- 公開する関数とクラスには docstring を書く。1 行目は「何をするか」、必要なら「なぜ」を足す。
  - 型注釈で分かることは書かない。
- `#` コメントは「なぜ」だけ。コードを読めば分かることは書かない。
- **Python の文法の説明はコメントに書かない。**
- `# =====` の見出しは、長い関数の段階の区切りにだけ使う。
- CLI の `main()` の docstring には実行コマンドを書く。
- コメントと docstring は日本語の文で書き、英語は識別子と固有名詞だけにする。
  - 日本語と英数字の間には半角スペースを入れる。
- import は「標準ライブラリ → 外部ライブラリ → このプロジェクト」の順に並べ、各グループの中はアルファベット順にする。
- **使わない import を残さない。** テストの `monkeypatch` が空振りし、本物の検索や Claude API が呼ばれる原因になる。

## 構成の取り決め

- `agent/` は `api/` を import しない。API と評価の両方が `agent/` を使う。
- Claude のクライアントとモデル名は `llm.py` から取る。
- Claude に渡す文章（システムプロンプト・ユーザーメッセージ）は `agent/prompts.py` に置く。
- 埋め込みモデルの読み込みと `passage:` / `query:` の付け分けは `retrieval/embeddings.py` に置く。
- 2 つ以上のファイルで使うパスは `paths.py` に置く。
- `evaluation/scoring.py` と `evaluation/metrics.py` からは、Claude API や埋め込みモデルにつながるものを import しない。
- 計算は LLM にさせず、Python のツールで行う。
- 投資助言、売買の判断、株価の予測はしない。

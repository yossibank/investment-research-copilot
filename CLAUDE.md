# investment-research-copilot

## 作業の進め方

- 変更したら `python -m pytest backend` を通す。
- 振る舞いを変えないリファクタリングでは、変更前の出力を先に記録し、変更後と比べる。
  - 比べる対象は、**変えた処理を実際に通るもの**にする。
- 評価は Claude API を呼ぶので、`--limit 3` で確かめてから全件を実行する。比較の基準は `evaluation/results/mvp-baseline.json`。
- プロンプトの文言は、リファクタリングのついでに変えない。変えたら評価を実行し直して比べる。

## コメント

- `__init__.py` 以外の `.py` の先頭に、モジュールの docstring を 1〜2 行書く。何が入っているかと、Claude API を呼ぶかどうかを書く。
- `src` の関数とクラスには docstring を書く。1 行目は「何をするか」。型注釈で分かることは書かない。
  - テスト関数は名前で内容を表す。docstring は、名前だけでは足りないときに書く。
- `#` コメントは「なぜ」だけ。**Python の文法の説明は書かない。**
- `# =====` の見出しは、長い関数の段階の区切りにだけ使う。
- CLI の `main()` の docstring には実行コマンドを書く。
- 日本語の文で書き、英語は識別子と固有名詞だけにする。日本語と英数字の間には半角スペースを入れる。

## 構成

- `agent/` は `api/` を import しない。API と評価の両方が `agent/` を使う。
- Claude を呼ぶときは、クライアントとモデル名を `llm.py` から取る。
- Copilot が Claude に渡す文章は `agent/prompts.py` に置く。
- 埋め込みモデルの読み込みと `passage:` / `query:` の付け分けは、`retrieval/embeddings.py` の中でも 1 か所だけで行う。
- 2 つ以上のファイルで使うパスは `paths.py` に置く。
- `evaluation/scoring.py` と `evaluation/metrics.py` は、Claude API や埋め込みモデルにつながるものを import しない。
- 使わない import を残さない。ファイルを移したあと移動元に残っていると、テストの `monkeypatch` が移動元を差し替えて空振りする。

## プロダクトの方針

- 計算は LLM にさせず、Python のツールで行う。
- 投資助言、売買の判断、株価の予測はしない。

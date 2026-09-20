# Learning Log

## 2026-09-19 - B1 Financial Metrics

### Learned

- pandasでCSVを読み込んだ
- 前期比をPythonで計算した
- 営業利益率を計算した
- pytestで計算ロジックを検証した
- Recall@5の意味を理解した

### Problems

- 特になし

### Tomorrow

- 決算資料からLLMで構造化データを抽出する

## 2026-09-20 - B2 Structured Extraction

### Learned

- Anthropic Python SDKを利用した
- Claude Structured Outputsを使った
- Pydanticを出力schemaとして利用した
- 決算短信から財務数値を抽出した
- API Timeout / Retryを設定した
- 欠損情報を推測せずnullとして扱った

### Architecture

Claude:
文章 → 構造化された事実

Python:
構造化された数値 → 正確な計算

### Important

資料に存在しない情報は推測しない。

LLM:
Extraction / Understanding

Python:
Calculation / Validation

### Problems

- 特になし

### Next

Embedding / Vector Search
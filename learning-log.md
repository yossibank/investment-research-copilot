# Learning Log

## 2026-09-19 - B1 Financial Metrics

### Learned

- pandasでCSVを読み込んだ
- 前期比をPythonで計算した
- 営業利益率を計算した
- pytestで計算ロジックを検証した
- Recall@5の意味を理解した

### Next

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

### Next

Embedding / Vector Search

## 2026-09-21 - B3 Vector Search

### Learned

- 決算PDFをpage単位でtext化した
- textをchunkへ分割した
- chunkにsource metadataを付与した
- multilingual-e5-smallでEmbeddingを作成した
- queryとpassageをvector化した
- cosine similarityでTop-K検索した
- Embeddingをcacheした

### Important

RAGでは回答生成より先に
「正しい根拠を取れるか」が重要。

質問
↓
Retrieval
↓
Context
↓
LLM

検索が失敗していれば、
LLMを改善しても正しい回答にはならない。

### Next

- 20件のGolden Setを作る
- Recall@5を測る
- Top-K chunkだけをClaudeへ渡す
- 根拠付き回答を生成する
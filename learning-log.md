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

## 2026-09-23 - B4 RAG Evaluation

### Learned

- B3 Vector SearchをRAGへ接続した
- Top-5 chunkだけをClaudeへ渡した
- Structured Outputで回答とsourceを取得した
- Golden Setを作成した
- Recall@5を測定した
- Answer Accuracyを測定した
- Source Match Rateを測定した
- 回答不能問題も評価した

### Important

RAGの品質は、

Retrieval
+
Generation

に分けて考える。

① 正しい根拠を取得できた？ → Retrieval

② 正しい根拠を渡したのに回答を間違えた？ → Generation

③ 解答は正しいのに、示した根拠が違う？ → Source Attribution

* Retrieval Error
  * 回答するために必要な根拠をVector Searchで取得できなかった
  * Recall@5の値が低い

```
元資料:
原材料価格の改善および価格改定効果により、
営業利益は前年同期比で増加しました。

正解Chunk:
company-p7-c1

検索結果:
company-p4-c0
「営業利益は132億円となりました」

company-p3-c2
「売上高は1,100億円となりました」

※ なぜ増えたのか分からない → Claude側のSystem Promptを何度直しても、根拠が渡っていないので改善しない
```

原因 | 具体例
:--: | :--:
Chunkが大きすぎる | 関係ない情報が大量に混ざる
Chunkが小さすぎる | 理由と結果が別Chunkに分離する
Overlap不足 | 文脈がChunk境界が切れる
Embeddingとの相性 | 日本語財務文書の意味をうまく捉えられない
Queryが曖昧 | 「利益について教えて」など
Top-Kが小さい | Rank6に正解があるのにTop5までしか取らない
PDF抽出が崩れている | 根拠自体がうまくテキスト化されていない

* Generation Error
  * 正しい根拠をClaudeへ渡したのに、Claudeが回答を間違えた
  * Promptを調整する

```
retrieval_hit = true

Top5:
company-p7-c1

原材料価格の改善及び価格改定効果により、
営業利益は増加しました

回答:
営業利益は売上高の増加によって増えました。

原因:
Prompt
Contextの渡し方
Claude Model
Output Schema
質問の曖昧さ
複数Chunk間の情報統合
```

* Source Attribution Error
  * 回答そのものは正しいが、Claudeが「この情報を使った」と示した出典が間違っている

```
正解:
company-p4-c0

回答:
{
  "answer": "営業利益は132億円です。",
  "is_answerable": true,
  "source_chunk_ids": [
    "company-p8-c0"
  ],
  "source_pages": [
    8
  ]
}

※ 正しい根拠はPage4でおかしい
```

### Baseline

Recall@5:
90%

Page Recall@5:
100%

Answer Accuracy:
95%

Source Match Rate:
90%

### Next

- FastAPIからRAGを呼ぶ
- SwiftUIから質問する
- 回答と資料名・ページを表示する

## 2026-09-23 - B5 FastAPI + SwiftUI

### Learned

- B4 RAGをFastAPIから呼び出した
- POST /research/queryを実装した
- PydanticでRequest / Responseを定義した
- Input Validationを追加した
- Claude API ErrorをHTTP Errorへ変換した
- TestClientでFastAPIをテストした
- Claude APIをMockしてAPI Testした
- SwiftUIからFastAPIへPOSTした
- JSONをCodableでdecodeした
- 回答とsource/pageをUIへ表示した
- API SecretをBackendだけで管理した

### Architecture

SwiftUI
↓
APIClient
↓
FastAPI
↓
RAG
↓
Vector Search
↓
Claude

### Security

ANTHROPIC_API_KEYはBackendの.envだけに置く。

iOS AppへSecretを埋め込まない。

### Important

LLM Outputをそのまま信用しない。

Claudeが返したsource_chunk_idは、
Backend側でも実際のretrieval resultsに
存在することを確認する。

### Next

- Streaming Response
- Structured Logging
- Request ID
- Latency計測
- GitHub公開準備
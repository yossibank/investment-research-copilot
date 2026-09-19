# Evaluation Notes

## Accuracy

全件のうち、正しかった割合。

## Precision

「正しい」と判定したもののうち、
実際に正しかった割合。

## Recall

本当に取得すべきものを、
どれだけ取りこぼさず取得できたか。

## F1

PrecisionとRecallのバランス。

## Recall@5

検索結果Top 5の中に、
正しい根拠が入っている割合。

Research Copilotでは、

Retrievalの評価
→ Recall@5

回答の評価
→ Answer Accuracy

として分離する。

回答が間違った場合に、

検索が悪かったのか
LLM生成が悪かったのか

を区別するため。
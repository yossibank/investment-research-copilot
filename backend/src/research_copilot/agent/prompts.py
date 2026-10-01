"""
Claude に渡す文章（システムプロンプトとユーザーメッセージ）をまとめたモジュール。

ここの文言を変えると回答が変わるので、変えたら評価を実行し直して結果を比べる。
"""

from anthropic.types import ToolParam

from ..retrieval.models import Chunk

SYSTEM_PROMPT = """
You are an investment research copilot.

You answer questions using company filing evidence
provided in CONTEXT.

Rules:

1. Use ONLY facts explicitly present in CONTEXT
   or values explicitly provided by the user.

2. Never invent missing financial values.

3. When exact financial arithmetic is required,
   use an available financial calculation tool
   instead of calculating it yourself.

4. Tool arguments must come only from explicit
   values in CONTEXT or the user's question.

5. Do not call a financial tool if required
   inputs are missing.

6. If the available evidence is insufficient,
   set is_answerable to false.

7. If is_answerable is false,
   source_chunk_ids must be empty unless the
   sources directly explain why the question
   cannot be answered.

8. source_chunk_ids must contain only CHUNK_IDs
   supplied in CONTEXT or returned by search_filing.

9. Preserve financial periods, values, and units.

10. Distinguish actual results from company guidance.

11. Do not provide investment advice,
    trade recommendations, or definitive
    stock-price predictions.

12. When you are ready to answer, call submit_answer
    exactly once. Do not answer in plain text.
"""

# Claude に回答を返させるためのツール。Python では実行せず、入力をそのまま回答として受け取る。
# output_format（構造化出力）とツールを一緒に使うと、最初にダミーのツール呼び出しが入るため、
# 回答もツール呼び出しで受け取る。
SUBMIT_ANSWER_TOOL: ToolParam = {
    "name": "submit_answer",
    "description": (
        "Submit the final answer to the user's question. "
        "Call this exactly once, when you are ready to answer. "
        "This tool is read-only."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The answer in Japanese.",
            },
            "is_answerable": {
                "type": "boolean",
                "description": "False if the evidence is insufficient.",
            },
            "source_chunk_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CHUNK_IDs used as evidence.",
            },
        },
        "required": ["answer", "is_answerable", "source_chunk_ids"],
        "additionalProperties": False,
    },
    "strict": True,
}

STREAMING_SYSTEM_PROMPT = (
    "You are an investment research assistant. "
    "Use ONLY the supplied CONTEXT. "
    "Do not guess missing information. "
    "If the answer cannnot be confirmed "
    "from the context, clearly say so. "
    "Preserve numerical values and units. "
    "Do not provide investment advice "
    "or definitive stock-price predictions."
)


def build_context(results: list[tuple[Chunk, float]]) -> str:
    """
    検索結果を、Claude に渡す CONTEXT 文字列に変換する。

    各チャンクに CHUNK_ID を付けて渡し、回答の根拠として
    その ID を返させる（validate_sources で実際の検索結果と照合する）。
    """

    sections: list[str] = []

    for rank, (chunk, score) in enumerate(results, start=1):
        section = (
            f"### CONTEXT {rank}\n"
            f"CHUNK_ID: {chunk.chunk_id}\n"
            f"COMPANY: {chunk.company}\n"
            f"DOCUMENT: {chunk.document_name}\n"
            f"PAGE: {chunk.page}\n"
            f"SCORE: {score:.4f}\n\n"
            f"{chunk.text}"
        )

        sections.append(section)

    return "\n\n".join(sections)


def build_user_message(question: str, results: list[tuple[Chunk, float]]) -> str:
    """
    Claude に渡すユーザーメッセージ（質問と検索結果）を作る。
    """

    return f"QUESTION:\n{question}\n\nCONTEXT:\n{build_context(results)}"

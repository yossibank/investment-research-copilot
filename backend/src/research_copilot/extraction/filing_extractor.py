"""
決算資料のテキストから、財務指標を構造化して抜き出す。Claude API を呼ぶ。
"""

import json

import anthropic

from ..llm import create_client, get_model
from ..paths import DATA_DIR
from .models import FilingExtraction

SAMPLE_PATH = DATA_DIR / "samples" / "sample_filing.txt"


def extract_filing(text: str) -> FilingExtraction:
    """
    決算資料のテキストから、売上高・営業利益・純利益・業績予想を Claude に抜き出させる。
    """

    if not text.strip():
        raise ValueError("Filing text must not be empty.")

    model = get_model()

    client = create_client()

    # output_format に渡した Pydantic の型に合う形で Claude に出力させ、検証して受け取る。
    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        system=(
            "You extract financial facts from company earnings filings "
            "Never guess missing information "
            "If a value is not present in the source, return null. "
            "Preserve the unit used in the source. "
            "Do not calculate values that are not explicitly stated. "
            "Do not mix actual results with company guidance. "
            "If no page number appears in the source, source_page must be null."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the financial information "
                    "from the following filing.\n\n"
                    f"{text}"
                ),
            }
        ],
        output_format=FilingExtraction,
    )

    result = response.parsed_output

    if result is None:
        raise RuntimeError("Structured output was not returned.")

    return result


def main() -> None:
    """
    data/samples/sample_filing.txt から抽出し、結果を JSON で表示する。

    実行: python -m research_copilot.extraction.filing_extractor
    """

    filing_text = SAMPLE_PATH.read_text(encoding="utf-8")

    try:
        result = extract_filing(filing_text)

    except anthropic.APITimeoutError:
        print("Claude API request timed out.")
        return

    except anthropic.RateLimitError:
        print("Claude API rate limit exceeded.")
        return

    except anthropic.APIConnectionError:
        print("Could not connect to Claude API.")
        return

    except anthropic.APIStatusError as error:
        print("Claude API error:", error.status_code)
        return

    except ValueError as error:
        print("Invalid input:", error)
        return

    print(
        json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

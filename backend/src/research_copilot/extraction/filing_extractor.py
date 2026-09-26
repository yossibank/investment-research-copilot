import json

import anthropic

from ..llm import create_client, get_model
from ..paths import DATA_DIR
from .models import FilingExtraction

SAMPLE_PATH = DATA_DIR / "samples" / "sample_filing.txt"


def extract_filing(text: str) -> FilingExtraction:
    # strip()
    #
    # 文字列の前後の空白・改行を削除する。
    if not text.strip():
        raise ValueError("Filing text must not be empty.")

    model = get_model()

    client = create_client()

    # pydanticモデルとして解析する。
    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        # Claudeにどういう役割で、どんなルールを守るのかの設定
        system=(
            "You extract financial facts from company earnings filings "
            "Never guess missing information "
            "If a value is not present in the source, return null. "
            "Preserve the unit used in the source. "
            "Do not calculate values that are not explicitly stated. "
            "Do not mix actual results with company guidance. "
            "If no page number appears in the source, source_page must be null."
        ),
        # Claudeへ実際に渡すユーザーメッセージ
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
        # フォーマット指定
        output_format=FilingExtraction,
    )

    # Pydanticで解析された結果を取得する。
    result = response.parsed_output

    if result is None:
        raise RuntimeError("Structured output was not returned.")

    return result


def main() -> None:
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

    # model_dump()
    #
    # dictに変換する。
    #
    # dumps()
    #
    # JSON文字列に変換する。
    print(
        json.dumps(
            result.model_dump(),
            # \u58f2\u4e0a → 売上高のように日本語を表示する。
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

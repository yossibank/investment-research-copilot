import json
import os
from pathlib import Path

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

from .models import FilingExtraction

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]

SAMPLE_PATH = BASE_DIR / "data" / "sample_filing.txt"

load_dotenv(REPO_ROOT / ".env")


def create_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    return Anthropic(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    )


def extract_filing(text: str) -> FilingExtraction:
    if not text.strip():
        raise ValueError("Filing text must not be empty.")

    model = os.getenv("ANTHROPIC_MODEL")

    if not model:
        raise RuntimeError("ANTHROPIC_MODEL is not set.")

    client = create_client()

    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        system=(
            "You extract financial facts from company earnings filings "
            "Never guess missing information "
            "If a value is not present in the source, return null."
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

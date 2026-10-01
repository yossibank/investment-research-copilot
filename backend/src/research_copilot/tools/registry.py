"""
Claude に渡すツールの定義と、要求されたツールを実行する入口（許可リスト）。
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from anthropic.types import ToolParam
from pydantic import BaseModel, ValidationError

from .filings_tool import ListFilingsInput, list_available_filings
from .financial_tool import calculate_growth_rate, calculate_operating_margin
from .models import GrowthRateInput, OperatingMarginInput
from .search_tool import SearchFilingInput, search_filing

TOOLS: list[ToolParam] = [
    {
        "name": "calculate_growth_rate",
        "description": (
            "Calculate the growth rate (%) of revenue or operating income "
            "from a previous-period value and a current-period value, "
            "with exact arithmetic. "
            "Call this ONLY when the question asks for the growth rate of "
            "revenue or operating income and the rate itself is not already "
            "stated in CONTEXT. "
            "Do not use it for other items such as gross profit, expenses, "
            "assets, or cash flows, and do not add growth rates the question "
            "did not ask for. "
            "Both values must be taken from CONTEXT or the user. "
            "This tool is read-only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "enum": ["revenue", "operating_income"],
                    "description": "Which item the two values are.",
                },
                "previous": {
                    "type": "number",
                    "description": "Value for the previous period.",
                },
                "current": {
                    "type": "number",
                    "description": "Value for the current period.",
                },
            },
            "required": ["item", "previous", "current"],
            "additionalProperties": False,
        },
        # 定義通りの入力を API に保証させる。空の入力 {} では呼べなくなる。
        "strict": True,
    },
    {
        "name": "calculate_operating_margin",
        "description": (
            "Calculate the operating margin (%) from revenue and operating "
            "income of the same period, with exact arithmetic. "
            "Call this ONLY when the question asks for an operating margin "
            "and the margin itself is not already stated in CONTEXT. "
            "Both values must be taken from CONTEXT or the user. "
            "This tool is read-only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "revenue": {
                    "type": "number",
                    "description": "Revenue for the period.",
                },
                "operating_income": {
                    "type": "number",
                    "description": "Operating income for the same period.",
                },
            },
            "required": ["revenue", "operating_income"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "search_filing",
        "description": (
            "Search the filings for passages that are not in CONTEXT. "
            "Call this ONLY when CONTEXT does not contain the information "
            "needed to answer. Do not call it to re-check facts already in CONTEXT. "
            "Returned passages have CHUNK_IDs that may be cited as sources. "
            "This tool is read-only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, in Japanese.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of passages to return (1-5).",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        # 空の入力 {} で呼ばれていたため、計算ツールと同じく定義通りの入力を保証させる。
        "strict": True,
    },
    {
        "name": "list_available_filings",
        "description": (
            "List the companies, periods, and documents that can be searched. "
            "Call this ONLY when the question names a company or period "
            "and CONTEXT does not show whether it is covered. "
            "This tool is read-only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]


@dataclass(frozen=True)
class ToolHandler:
    """
    許可したツール 1 つ分の入力の型と実行する関数の組。
    """

    input_model: type[BaseModel]
    run: Callable[[Any], BaseModel]


# 許可リスト。ここにはないツール名は、Claude が要求しても実行しない。
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "calculate_growth_rate": ToolHandler(
        input_model=GrowthRateInput,
        run=calculate_growth_rate,
    ),
    "calculate_operating_margin": ToolHandler(
        input_model=OperatingMarginInput,
        run=calculate_operating_margin,
    ),
    "search_filing": ToolHandler(
        input_model=SearchFilingInput,
        run=search_filing,
    ),
    "list_available_filings": ToolHandler(
        input_model=ListFilingsInput,
        run=list_available_filings,
    ),
}


def run_tool(
    name: str,
    tool_input: dict,
) -> BaseModel:
    """
    Claude が要求したツールを実行し、結果を型のまま返す。

    ツール名を許可リストと照合し、許可したツールだけを実行する。
    入力も Pydantic で検証してから渡す。
    """

    handler = TOOL_HANDLERS.get(name)

    if handler is None:
        raise ValueError(f"Unknown tool: {name}")

    try:
        validated_input = handler.input_model.model_validate(tool_input)

    except ValidationError as error:
        raise ValueError(f"Invalid input for tool: {name}") from error

    return handler.run(validated_input)


def execute_tool(
    name: str,
    tool_input: dict,
) -> str:
    """
    run_tool の結果を、Claude に返す JSON 文字列にする。
    """

    result = run_tool(
        name=name,
        tool_input=tool_input,
    )

    return json.dumps(
        result.model_dump(),
        ensure_ascii=False,
    )

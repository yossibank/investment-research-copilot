import json

from anthropic.types import ToolParam
from pydantic import ValidationError

from .financial_tool import calculate_financial_metrics
from .models import FinancialMetricsInput

TOOLS: list[ToolParam] = [
    {
        "name": "calculate_financial_metrics",
        "description": (
            "Calculate financial growth rates and "
            "operating margins from available revenue "
            "and operating income values. "
            "Provide only values explicitly available "
            "from the user or filing context. "
            "Do not invent missing values. "
            "Missing inputs may be omitted. "
            "Metrics that cannot be calculated will return null. "
            "This tool is read-only."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "previous_revenue": {
                    "type": "number",
                    "description": "Revenue for the previous period.",
                },
                "current_revenue": {
                    "type": "number",
                    "description": "Revenue for the current period.",
                },
                "previous_operating_income": {
                    "type": "number",
                    "description": "Operating income for the previous period.",
                },
                "current_operating_income": {
                    "type": "number",
                    "description": "Operating income for the current period.",
                },
            },
        },
    }
]


def execute_tool(
    name: str,
    tool_input: dict,
) -> str:
    """
    Claude が要求したツールを実行し、結果を JSON 文字列で返す。

    ツール名を許可リストと照合し、許可したツールだけを実行する。
    入力も Pydantic で検証してから渡す。
    """

    if name != "calculate_financial_metrics":
        raise ValueError(f"Unknown tool: {name}")

    try:
        validated_input = FinancialMetricsInput.model_validate(tool_input)

    except ValidationError as error:
        raise ValueError("Invalid financial tool input.") from error

    result = calculate_financial_metrics(validated_input)

    return json.dumps(
        result.model_dump(),
        ensure_ascii=False,
    )

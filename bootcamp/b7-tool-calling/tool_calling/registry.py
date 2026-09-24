import json

from pydantic import ValidationError

from .financial_tool import calculate_financial_metrics
from .models import FinancialMetricsInput

TOOLS = [
    {
        "name": "calculate_financial_metrics",
        "description": (
            "Calculate deterministic financial "
            "metrics from previous and current "
            "revenue and operating income. "
            "Use this tool when the user asks "
            "for revenue growth, operating "
            "income growth, or operating margin. "
            "The tool performs arithmetic only "
            "and does not modify any data."
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
            "required": [
                "previous_revenue",
                "current_revenue",
                "previous_operating_income",
                "current_operating_income",
            ],
        },
    }
]


def execute_tool(
    name: str,
    tool_input: dict,
) -> str:
    """
    Claudeが要求したToolを実行するDispatcher。

    Tool名をClaudeから直接execするのではなく、
    allowlistで明示的に許可したToolだけを実行する。
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

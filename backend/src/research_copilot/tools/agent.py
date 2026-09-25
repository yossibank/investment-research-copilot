import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from ..paths import ENV_PATH
from .registry import TOOLS, execute_tool

load_dotenv(ENV_PATH)


def create_client() -> Anthropic:
    """
    Anthropic Clientを生成する。
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    return Anthropic(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    )


def extract_text(response) -> str:
    """
    Claude Reponseからtext blockだけを連結する。
    """

    texts = [block.text for block in response.content if block.type == "text"]

    return "\n".join(texts)


def run_agent(
    user_message: str,
    max_tool_rounds: int = 3,
) -> str:
    """
    Claude + Client Toolの基本Loop。

    1. User MessageをClaudeへ送る
    2. Claudeがtool_useを返したらPythonでTool実行
    3. tool_resultをClaudeへ返す
    4. ClaudeがFinal Answerを生成

    Toolが不要なら、そのままFinal Answerを返す。
    """

    if not user_message.strip():
        raise ValueError("User message must not be empty.")

    model = os.getenv("ANTHROPIC_MODEL")

    if not model:
        raise RuntimeError("ANTHROPIC_MODEL is not set.")

    client = create_client()

    messages: list[dict] = [{"role": "user", "content": user_message}]

    for _ in range(max_tool_rounds + 1):
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=(
                "You are an investment research assistant. "
                "Use the financial calculation tool whenever "
                "exact financial arithmetic is required. "
                "Do not perform financial arithmetic yourself when "
                "the tool can perform it. "
                "Do not invent missing numeric inputs."
                "If required inputs are missing, "
                "ask the user for the missing information. "
                "The available tool is read-only and does not modify data. "
                "Do not provide investment advice or definitive stock-price predictions."
            ),
            tools=TOOLS,
            tool_choice={
                "type": "auto",
                "disable_parallel_tool_use": True,
            },
            messages=messages,
        )

        # Toolを要求しなかった場合、Final Answerとして返す。
        if response.stop_reason != "tool_use":
            return extract_text(response)

        # ResponseそのものをConversation Historyへ追加する。
        messages.append(
            {
                "role": "assistant",
                "content": response.content,
            }
        )

        tool_results: list[dict] = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            try:
                result = execute_tool(
                    name=block.name,
                    tool_input=block.input,
                )

                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                }

            except Exception as error:
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": {f"Tool execution failed: {type(error).__name__}"},
                    "is_error": True,
                }

            tool_results.append(tool_result)

        messages.append(
            {
                "role": "user",
                "content": tool_results,
            }
        )

    raise RuntimeError("Maximum tool rounds exceeded.")

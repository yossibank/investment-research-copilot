import os

from anthropic import Anthropic
from dotenv import load_dotenv

from .paths import ENV_PATH

# モジュールを最初にimportしたときに1回だけ実行される。
load_dotenv(ENV_PATH)


def create_client() -> Anthropic:
    """
    Claude API Clientを生成する。
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    return Anthropic(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    )


def get_model() -> str:
    """
    使用するClaudeのモデル名を環境変数から取得する。

    呼ばれるたびに読むので、実行中に環境変数を変えても反映される。
    """

    model = os.getenv("ANTHROPIC_MODEL")

    if not model:
        raise RuntimeError("ANTHROPIC_MODEL is not set.")

    return model

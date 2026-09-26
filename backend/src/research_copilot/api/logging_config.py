import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """
    ログを 1 行 1 JSON で出力する。

    JSON にしておけば、後から検索や集計（p50 / p95 など）がしやすい。
    extra で渡した値のうち、fields に書いた項目だけを出力する。
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        fields = [
            "event",
            "request_id",
            "method",
            "path",
            "status_code",
            "latency_ms",
            "retrieval_ms",
            "top_k",
            "input_tokens",
            "output_tokens",
            # ツール用
            "tool_name",
            "tool_success",
            "tool_latency_ms",
            "tool_output",
        ]

        for field in fields:
            if hasattr(record, field):
                payload[field] = getattr(
                    record,
                    field,
                )

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            ensure_ascii=False,
        )


def configure_logging() -> None:
    """
    アプリ全体のログを JsonFormatter で出力するよう設定する。
    """

    handler = logging.StreamHandler()

    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()

    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()

    root_logger.addHandler(handler)

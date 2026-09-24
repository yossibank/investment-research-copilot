import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """
    PythonのLogRecordを1行JSONへ変換するFormatter。

    Cloud Logging等へ移行した場合も、
    JSON Logなら機械的に検索・集計しやすい。
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
    Application全体のLogging設定。
    """

    handler = logging.StreamHandler()

    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()

    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()

    root_logger.addHandler(handler)

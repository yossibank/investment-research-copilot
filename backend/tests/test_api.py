from fastapi.testclient import TestClient
from research_copilot.api.main import app
from research_copilot.api.schemas import (
    CopilotQueryResponse,
    ResearchQueryResponse,
    ResearchSource,
)
from research_copilot.api.streaming_service import json_line

client = TestClient(app)


def test_health() -> None:
    """
    Health Checkが成功することを確認する。
    """

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {"status": "ok"}


def test_research_query(monkeypatch) -> None:
    """
    Claudeを呼ばずにAPI Endpointだけをテストする。
    """

    def fake_run_research_query(
        question: str,
        top_k: int,
    ) -> ResearchQueryResponse:
        # 固定レスポンス
        return ResearchQueryResponse(
            answer="営業利益は132億円です。",
            is_answerable=True,
            sources=[
                ResearchSource(
                    chunk_id="company-p4-c0",
                    company="Sample Holdings株式会社",
                    document_name="2026年3月期 決算短信",
                    page=4,
                    score=0.85,
                    source_url="https://example.com",
                )
            ],
        )

    # Fakeへ差し替える。
    monkeypatch.setattr(
        "research_copilot.api.main.run_research_query",
        fake_run_research_query,
    )

    response = client.post(
        "/research/query",
        json={
            "question": "営業利益はいくらですか？",
            "top_k": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["is_answerable"] is True

    assert body["answer"] == "営業利益は132億円です。"

    assert body["sources"][0]["page"] == 4


def test_copilot_endpoint(monkeypatch) -> None:
    def fake_run_copilot_query(
        question: str,
        top_k: int,
        request_id: str | None = None,
    ) -> CopilotQueryResponse:
        return CopilotQueryResponse(
            answer="今期の営業利益率は12.0%です。",
            is_answerable=True,
            sources=[
                ResearchSource(
                    chunk_id="company-p4-c0",
                    company="Example Holdings",
                    document_name="2026年3月期 決算短信",
                    page=4,
                    score=0.88,
                    source_url="https://example.com",
                )
            ],
            tools_used=[
                "calculate_financial_metrics",
            ],
        )

    monkeypatch.setattr(
        "research_copilot.api.main.run_copilot_query",
        fake_run_copilot_query,
    )

    response = client.post(
        "/research/copilot",
        json={
            "question": "今期の営業利益率は？",
            "top_k": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["is_answerable"] is True

    assert "calculate_financial_metrics" in body["tools_used"]

    assert body["sources"][0]["page"] == 4


def test_empty_question() -> None:
    """
    空白だけの質問がValidation Errorになることを確認する。
    """

    response = client.post(
        "/research/query",
        json={
            "question": "   ",
            "top_k": 5,
        },
    )

    assert response.status_code == 422


def test_json_line() -> None:
    result = json_line(
        {
            "type": "text_delta",
            "text": "営業利益",
        }
    )

    assert result.endswith("\n")
    assert '"type": "text_delta"' in result

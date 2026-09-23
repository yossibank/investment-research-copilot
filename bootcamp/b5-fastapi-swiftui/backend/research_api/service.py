from rag_evaluation.rag import answer_question

from .schemas import ResearchQueryResponse, ResearchSource


def run_research_query(
    question: str,
    top_k: int,
) -> ResearchQueryResponse:
    """
    B4 RAGを実行し、API Responseへ変換する。
    FastAPI自身にはRAGの詳細を持たせない。

    main.py:
        HTTP担当

    service.py:
        Application Logic担当

    rag.py:
        AI / RAG担当
    """

    answer, retrieved = answer_question(question=question, top_k=top_k)

    # Retrieval結果をchunk_idで検索できるDictionaryへ変換する。
    #
    # 例:
    #
    # {
    #   "company-p4-c0":
    #       (Chunk(...), 0.85)
    # }
    retrieved_by_id = {
        chunk.chunk_id: (
            chunk,
            score,
        )
        for chunk, score in retrieved
    }

    sources: list[ResearchSource] = []

    # 同じsourceIDが複数返った場合に重複表示しないために利用する。
    seen_ids: set[str] = set()

    # Claudeが「回答根拠として使った」と返したchunk_idだけを見る。
    for chunk_id in answer.source_chunk_ids:
        if chunk_id in seen_ids:
            continue

        # Claudeが返したIDをそのまま信用しない。
        # 本当にRetrieval結果の中に存在するかを確認する。
        retrieved_item = retrieved_by_id.get(chunk_id)

        if retrieved_item is None:
            continue

        chunk, score = retrieved_item

        sources.append(
            ResearchSource(
                chunk_id=chunk.chunk_id,
                company=chunk.company,
                document_name=chunk.document_name,
                page=chunk.page,
                score=score,
                source_url=chunk.source_url,
            )
        )

        seen_ids.add(chunk_id)

    return ResearchQueryResponse(
        answer=answer.answer,
        is_answerable=answer.is_answerable,
        sources=sources,
    )

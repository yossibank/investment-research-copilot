from rag_evaluation.evaluator import contains_required_terms, normalize_text


def test_normalize_text() -> None:
    """
    空白やカンマなどの表記揺れを
    正規化できることを確認する。
    """

    assert normalize_text("売上高 1,100 億円") == "売上高1100億円"


def test_contains_required_terms() -> None:
    """
    必要な情報が全て含まれていれば
    Trueになることを確認する。
    """

    answer = "売上高は1,100億円です。"

    assert contains_required_terms(answer, ["売上高", "1100億円"])


def test_missing_required_term() -> None:
    """
    必要な情報が1つでも欠けていれば
    Falseになることを確認する。
    """

    answer = "売上高は1,100億円です。"

    assert not contains_required_terms(answer, ["営業利益", "1100億円"])


def test_empty_required_terms() -> None:
    """
    required_terms=[]の場合、all([])はTrueになる。
    """

    assert contains_required_terms("資料からは確認できません。", [])

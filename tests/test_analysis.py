from ally.analysis import tokenize, top_terms


def test_hyphen_token() -> None:
    tokens = tokenize("привет-мир и the world")
    assert "привет-мир" in tokens
    assert "и" not in tokens


def test_top_terms_limit() -> None:
    terms = top_terms("a b c d e")
    assert len(terms) <= 3

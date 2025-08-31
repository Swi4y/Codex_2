from ally.analysis import tokenize, top_terms


def test_tokenize_and_terms():
    text = "Привет, мир! This is a test"
    tokens = tokenize(text)
    assert "привет" in tokens
    assert "this" not in tokens
    terms = top_terms(tokens, 2)
    assert len(terms) == 2

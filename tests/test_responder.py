from ally.responder import respond


def test_response_format():
    msg = respond(["мир", "привет"], style="gentle")
    assert msg.startswith("нити: мир")
    assert "вопрос:" in msg

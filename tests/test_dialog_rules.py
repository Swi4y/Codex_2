from tempfile import TemporaryDirectory

from ally.service import create_entry, init_storage


def test_escalates_on_repeat_topic() -> None:
    with TemporaryDirectory() as d:
        init_storage(d)
        create_entry(text="тема повторяется", dialog="rules", style="gentle", path=d)
        _, reply = create_entry(text="снова эта тема", dialog="rules", style="gentle", path=d)
        assert "возвращаетесь" in reply

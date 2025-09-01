from tempfile import TemporaryDirectory

from ally.service import create_entry, init_storage


def test_negative_pool() -> None:
    with TemporaryDirectory() as d:
        init_storage(d)
        _, reply = create_entry(text="это плохо и ужасно", dialog="sentiment", style="gentle", path=d)
        assert "поддержать" in reply


def test_positive_pool() -> None:
    with TemporaryDirectory() as d:
        init_storage(d)
        _, reply = create_entry(text="всё отлично и прекрасно", dialog="sentiment", style="gentle", path=d)
        assert "радует" in reply

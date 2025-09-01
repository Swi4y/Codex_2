from click.testing import CliRunner
from tempfile import TemporaryDirectory

from ally.cli import cli


def test_write_command_creates_entry() -> None:
    runner = CliRunner()
    with TemporaryDirectory() as d:
        runner.invoke(cli, ["--path", d, "init"])
        result = runner.invoke(
            cli, ["--path", d, "write", "Сегодня всё хорошо"], input=""
        )
        assert "вопрос:" in result.output
        assert "нити:" in result.output

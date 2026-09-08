from argparse import Namespace
from pathlib import Path

from dtri_meeting_room import cli


def test_custom_skill_destination_creates_a_named_skill_directory(tmp_path: Path) -> None:
    assert cli._skill_destination(str(tmp_path)) == tmp_path.resolve() / "dtri-meeting-room"


def test_claude_and_anthropic_resolve_to_the_same_project_local_destination() -> None:
    assert cli._skill_destination("claude") == cli._skill_destination("anthropic")


def test_install_skill_copies_only_skill_markdown_and_refuses_overwrite(tmp_path: Path) -> None:
    original_source = cli.SKILL_SOURCE
    cli.SKILL_SOURCE = Path(__file__).parents[1] / "src" / "dtri_meeting_room" / "skills" / "dtri-meeting-room" / "SKILL.md"
    args = Namespace(destination=str(tmp_path), force=False)
    try:
        cli._install_skill(args)
        target = tmp_path / "dtri-meeting-room" / "SKILL.md"
        assert target.read_text(encoding="utf-8").startswith("---\nname: dtri-meeting-room")
        try:
            cli._install_skill(args)
        except SystemExit as error:
            assert "Refusing to overwrite" in str(error)
        else:
            raise AssertionError("existing SKILL.md was overwritten without --force")
    finally:
        cli.SKILL_SOURCE = original_source

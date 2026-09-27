"""The pre-0.4.0 name still works.

This tool was called `truthgate` until 0.4.0. Three repos on disk carry a
`.truthgate.toml` written before the rename, so the compatibility path in
`policy.DEFAULT_CONFIG_NAMES` is load-bearing, not decorative -- and a fallback
nobody exercises is a fallback that rots. These tests fail if it is removed.
"""

from pathlib import Path

from trvthnvke.gitutil import find_root
from trvthnvke.policy import DEFAULT_CONFIG_NAMES, load_policy

_POLICY = """\
[policy]
fail_on = "error"

[[docs]]
path = "README.md"
"""


def test_legacy_config_name_is_accepted(tmp_path: Path) -> None:
    (tmp_path / ".truthgate.toml").write_text(_POLICY, encoding="utf-8")
    policy = load_policy(tmp_path)
    assert [d.path for d in policy.docs] == ["README.md"]


def test_new_config_name_wins_when_both_exist(tmp_path: Path) -> None:
    (tmp_path / ".truthgate.toml").write_text(_POLICY, encoding="utf-8")
    (tmp_path / ".trvthnvke.toml").write_text(
        _POLICY.replace("README.md", "DOCS.md"), encoding="utf-8"
    )
    policy = load_policy(tmp_path)
    assert [d.path for d in policy.docs] == ["DOCS.md"]


def test_new_name_is_preferred_in_the_search_order() -> None:
    assert DEFAULT_CONFIG_NAMES[0] == ".trvthnvke.toml"
    assert ".truthgate.toml" in DEFAULT_CONFIG_NAMES
    assert DEFAULT_CONFIG_NAMES.index(".trvthnvke.toml") < DEFAULT_CONFIG_NAMES.index(
        ".truthgate.toml"
    )


def test_root_discovery_honours_a_legacy_config(tmp_path: Path) -> None:
    """A checkout with no .git and only the old config name still resolves."""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (tmp_path / ".truthgate.toml").write_text(_POLICY, encoding="utf-8")
    assert find_root(nested) == tmp_path


def test_legacy_module_is_importable() -> None:
    """`python -m truthgate` is in the default command allowlist, so it must run."""
    import truthgate

    from trvthnvke import __version__

    assert truthgate.__version__ == __version__


def test_legacy_module_runs_as_main() -> None:
    import subprocess
    import sys
    from pathlib import Path

    src = str(Path(__file__).resolve().parent.parent / "src")
    out = subprocess.run(
        [sys.executable, "-m", "truthgate", "--version"],
        capture_output=True, text=True, env={"PYTHONPATH": src, "PATH": "/usr/bin:/bin"},
    )
    assert out.returncode == 0, out.stderr
    assert "trvthnvke" in out.stdout

import signal
import threading
from pathlib import Path

from truthgate.model import Claim
from truthgate.policy import Policy
from truthgate.security import RegexTimeout, bounded_regex_search
from truthgate.verify import check_claim


def _claim(**attrs) -> Claim:
    return Claim(
        id="x",
        kind="file_contains",
        source="fence",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs=attrs,
        body=f"see `{attrs.get('path', '')}`",
    )


def test_literal_default_dot_is_not_wildcard(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("a.c\n", encoding="utf-8")
    policy = Policy(root=tmp_path, require_lock=False)

    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", pattern="a.c"), policy)
    assert ok, evidence

    f.write_text("abc\n", encoding="utf-8")
    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", pattern="a.c"), policy)
    assert not ok, evidence

    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", regex="a.c"), policy)
    assert ok, evidence


def test_ignore_case_literal(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("HELLO world\n", encoding="utf-8")
    policy = Policy(root=tmp_path, require_lock=False)
    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", pattern="hello", ignore_case="true"), policy)
    assert ok, evidence
    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", pattern="hello"), policy)
    assert not ok, evidence


def test_pattern_and_regex_both_given_fails(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("abc\n", encoding="utf-8")
    policy = Policy(root=tmp_path, require_lock=False)
    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", pattern="a", regex="a"), policy)
    assert not ok
    assert "not both" in evidence


def test_bounded_regex_search_timeout() -> None:
    if not (threading.current_thread() is threading.main_thread() and hasattr(signal, "setitimer")):
        return
    try:
        bounded_regex_search(r"(a+)+$", "a" * 40 + "!", 0, 0.2)
        raise AssertionError("expected RegexTimeout")
    except RegexTimeout:
        pass
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_check_claim_regex_timeout_end_to_end(tmp_path: Path) -> None:
    if not (threading.current_thread() is threading.main_thread() and hasattr(signal, "setitimer")):
        return
    f = tmp_path / "f.txt"
    f.write_text("a" * 40 + "!\n", encoding="utf-8")
    policy = Policy(root=tmp_path, require_lock=False, regex_timeout_sec=0.2)
    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", regex=r"(a+)+$"), policy)
    assert (ok, evidence) == (False, "pattern timed out")
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_pattern_too_long(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("abc\n", encoding="utf-8")
    policy = Policy(root=tmp_path, require_lock=False)
    long_pattern = "a" * 257
    ok, evidence = check_claim(tmp_path, _claim(path="f.txt", pattern=long_pattern), policy)
    assert not ok
    assert "too long" in evidence

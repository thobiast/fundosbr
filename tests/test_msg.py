# -*- coding: utf-8 -*-
"""Test msg function."""

import sys
import pytest
from fundosbr.fundosbrlib import msg


@pytest.mark.parametrize(
    "color, text, result",
    [
        ("red", "test", "\033[1;31mtest\033[0m\n"),
        ("blue", "test", "\033[0;34mtest\033[0m\n"),
        ("yellow", "test", "\033[0;33mtest\033[0m\n"),
        ("", "test", "test\n"),
        ("nocolor", "test", "test\n"),
    ],
)
def test_msg(capsys, color, text, result):
    """Test msg function."""
    msg(color, text)
    captured = capsys.readouterr()
    assert captured.out == result


@pytest.mark.parametrize(
    "color, text, result",
    [
        ("red", "test", "\033[1;31mtest\033[0m\n"),
        ("blue", "test", "\033[0;34mtest\033[0m\n"),
        ("yellow", "test", "\033[0;33mtest\033[0m\n"),
        ("", "test", "test\n"),
        ("nocolor", "test", "test\n"),
    ],
)
def test_msg_stderr(capsys, color, text, result):
    """Test print to stderr."""
    msg(color, text, output=sys.stderr)
    captured = capsys.readouterr()
    assert captured.err == result


@pytest.mark.parametrize(
    "color, text, end, result",
    [
        ("", "test", "", "test"),
        ("nocolor", "test", "--", "test--"),
        ("blue", "test", "", "\033[0;34mtest\033[0m"),
    ],
)
def test_msg_end(capsys, color, text, end, result):
    """Test end parameter."""
    msg(color, text, end=end)
    out, err = capsys.readouterr()
    assert out == result


@pytest.mark.parametrize(
    "color, text, retcode",
    [
        ("red", "test", 8),
        ("", "test", 10),
        ("blue", "test", 2),
    ],
)
def test_msg_exit(color, text, retcode):
    """Test exit code."""
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        msg(color, text, retcode)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == retcode


def test_msg_error():
    """Test invalid color."""
    with pytest.raises(ValueError, match="Invalid color"):
        msg("invalid_color", "test")


# vim: ts=4

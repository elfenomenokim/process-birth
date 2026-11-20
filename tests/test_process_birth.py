import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import process_birth as pb  # noqa: E402

posix_only = pytest.mark.skipif(os.name == "nt", reason="ps and /proc do not exist on Windows")
linux_only = pytest.mark.skipif(not os.path.isdir("/proc/self"), reason="needs Linux /proc")


# --- epoch: text and integers -----------------------------------------------------


def test_c_ps_text_parses_in_utc():
    assert pb.epoch("Fri Nov 20 03:00:00 2026", legacy_zone="UTC") == 1795143600


def test_space_padded_day_and_extra_spaces_parse():
    assert pb.epoch("Sun Nov  1  12:00:00   2026", legacy_zone="UTC") == 1793534400


def test_wrong_weekday_is_rejected():
    assert pb.epoch("Mon Nov 20 03:00:00 2026", legacy_zone="UTC") is None


def test_impossible_date_and_garbage_are_none():
    assert pb.epoch("Fri Feb 30 03:00:00 2026", legacy_zone="UTC") is None
    assert pb.epoch("not a date") is None
    assert pb.epoch("") is None


def test_korean_ps_text_parses():
    assert pb.epoch("2026년 11월 20일 금요일 03시 00분 00초", legacy_zone="UTC") == 1795143600


def test_integers_and_digit_strings_pass_through():
    assert pb.epoch(1795143600) == 1795143600
    assert pb.epoch("1795143600") == 1795143600
    assert pb.epoch(0) is None
    assert pb.epoch(-5) is None
    assert pb.epoch(True) is None
    assert pb.epoch(None) is None


def test_custom_weekday_table():
    french = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
    assert pb.epoch("Fri Nov 20 03:00:00 2026", legacy_zone="UTC", weekdays=french) == 1795143600
    with pytest.raises(ValueError):
        pb.epoch("Fri Nov 20 03:00:00 2026", weekdays=["a", "b"])


def test_unknown_zone_is_an_error():
    with pytest.raises(ValueError):
        pb.epoch("Fri Nov 20 03:00:00 2026", legacy_zone="Asia/Seoul")


# --- same and target_text ---------------------------------------------------------


def test_missing_observations_never_match():
    assert pb.same(None, None) is False
    assert pb.same("garbage", "garbage") is False


def test_same_instant_in_two_shapes_matches():
    assert pb.same("Fri Nov 20 03:00:00 2026", 1795143600, first_zone="UTC")


def test_target_text_keeps_saved_text_and_renders_epochs():
    assert pb.target_text("Fri Nov 20 03:00:00 2026") == "Fri Nov 20 03:00:00 2026"
    rendered = pb.target_text(1795143600)
    assert pb.epoch(rendered) == 1795143600
    assert pb.target_text(0) == ""
    assert pb.target_text(1795143600, render=lambda value: f"t{value}") == "t1795143600"


# --- read: live processes --------------------------------------------------------


def test_read_own_process_is_recent():
    birth = pb.read(os.getpid())
    assert birth is not None
    assert 0 <= int(time.time()) - birth < 3600


def test_read_accepts_a_decimal_string_pid():
    assert pb.read(str(os.getpid())) == pb.read(os.getpid())


def test_read_rejects_bools_and_bad_values():
    for value in (True, False, 0, -1, "abc", "", None, 1.5):
        assert pb.read(value) is None


def test_read_of_a_finished_process_is_none():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    del child  # releases the Windows process handle so the PID is really gone
    assert pb.read(2_147_483_000) is None


def test_child_started_later_is_not_the_same_process():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
    try:
        birth = pb.read(child.pid)
        assert birth is not None
        assert birth >= pb.read(os.getpid())
    finally:
        child.kill()
        child.wait()


# --- snapshot -------------------------------------------------------------------


@posix_only
def test_snapshot_contains_this_process_with_its_parent():
    rows = pb.snapshot()
    birth, parent = rows[os.getpid()]
    assert birth == pb.read(os.getpid())
    assert parent == os.getppid()


@pytest.mark.skipif(os.name != "nt", reason="Windows behaviour")
def test_snapshot_on_windows_is_a_clear_error():
    with pytest.raises(OSError):
        pb.snapshot()


# --- Linux without ps -----------------------------------------------------------


@linux_only
def test_proc_fallback_matches_ps(monkeypatch):
    with_ps = pb.read(os.getpid())
    rows_with_ps = pb.snapshot()

    def no_ps(*args, **kwargs):
        raise FileNotFoundError("ps")

    monkeypatch.setattr(pb.subprocess, "run", no_ps)
    assert pb.read(os.getpid()) == with_ps
    rows = pb.snapshot()
    assert rows[os.getpid()] == rows_with_ps[os.getpid()]

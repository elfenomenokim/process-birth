"""Process birth identity: integer UTC seconds from a process start time.

A PID alone is not an identity: the operating system reuses it. This module
turns `ps` start times and saved text into one integer (Unix UTC seconds), so two
observations compare equal only when they describe the same process.

Two behaviour rules matter more than the parsing:

* An unknown or invalid value never compares equal to anything, including another
  missing value. A failed read is not evidence of sameness.
* The saved address text (`target_text`) is a legacy hash input, not an identity.
  Keep its shape stable for values written by older versions.

The module is standard library only. Locale-specific weekday tables and date
formats are caller supplied, so a host whose `ps` prints another language is
configured, not patched: pass `weekdays=` for other weekday names, or `parse=`
with your own reader for another date shape entirely.
"""
import calendar
import datetime
import os
import re
import subprocess
import time

MONTHS = dict(zip('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), range(1, 13)))
WEEKDAYS = 'Mon Tue Wed Thu Fri Sat Sun'.split()
PS_ENV = {**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC'}

# Weekday names of the localized formats below, indexed Monday first to match
# `datetime.weekday()` and `time.struct_time.tm_wday`. Pass your own table to
# `epoch()`, `same()` or `target_text()` when the host is in another locale.
KO_WEEKDAYS = list('월화수목금토일')
_WEEKDAY_TABLES = [WEEKDAYS, KO_WEEKDAYS]

# Built-in non-C date shapes. Each pattern yields
# (year, month, day, weekday name, hour, minute, second).
_LOCALIZED_FORMATS = (
    re.compile(r'(\d{4})년 (\d{1,2})월 (\d{1,2})일 ([월화수목금토일])요일 (\d{2})시 (\d{2})분 (\d{2})초'),
)


def _custom(text, tables, parse):
    """Let a caller supply the reader for a date shape this module does not know.

    `parse(text)` returns `(year, month, day, weekday name, hour, minute, second)`
    or None. A weekday name of None skips the weekday cross-check.
    """

    parsed = parse(text)
    if not parsed or len(parsed) != 7:
        return None
    year, month, day, weekday, hour, minute, second = parsed
    try:
        instant = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    except (TypeError, ValueError, OverflowError):
        return None
    if weekday is None:
        return instant
    index = _weekday_index(weekday, tables)
    if index is None or instant.weekday() != index:
        return None
    return instant


def _weekday_tables(weekdays):
    """Accept one weekday table or several; the C `ps` names always remain valid.

    A table is seven names in one flat sequence; several tables are a sequence of
    such sequences. The two shapes stay distinguishable so a caller passing
    `['lun', 'mar', ...]` is not read as seven single-letter tables.
    """

    if weekdays is None:
        return _WEEKDAY_TABLES
    if isinstance(weekdays, str):
        tables = [list(weekdays)]
    else:
        items = list(weekdays)
        if items and all(isinstance(item, str) for item in items):
            tables = [items]
        else:
            tables = [list(table) for table in items]
    for table in tables:
        if len(table) != 7 or not all(isinstance(name, str) and name for name in table):
            raise ValueError('a weekday table must hold seven non-empty names, Monday first')
    return [WEEKDAYS] + [table for table in tables if table != WEEKDAYS]


def _weekday_index(weekday, tables):
    for table in tables:
        if weekday in table:
            return table.index(weekday)
    return None


def epoch(value, *, legacy_zone='local', weekdays=None, parse=None):
    if legacy_zone not in ('local', 'UTC'):
        raise ValueError('legacy timezone must be local or UTC')
    if type(value) is int:
        return value if value > 0 else None
    if not isinstance(value, str):
        return None
    value = ' '.join(value.split())
    if value.isascii() and value.isdigit():
        return int(value) if int(value) > 0 else None
    tables = _weekday_tables(weekdays)
    en = re.fullmatch(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{1,2}) (\d{2}):(\d{2}):(\d{2}) (\d{4})', value)
    try:
        instant = None
        if en:
            weekday, month, day, hour, minute, second, year = en.groups()
            candidate = datetime.datetime(int(year), MONTHS[month], int(day), int(hour), int(minute), int(second))
            index = _weekday_index(weekday, tables)
            if index is not None and candidate.weekday() == index:
                instant = candidate
        else:
            for pattern in _LOCALIZED_FORMATS:
                match = pattern.fullmatch(value)
                if match is None:
                    continue
                year, month, day, weekday, hour, minute, second = match.groups()
                candidate = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                index = _weekday_index(weekday, tables)
                if index is not None and candidate.weekday() == index:
                    instant = candidate
                break
            if instant is None and parse is not None:
                instant = _custom(value, tables, parse)
        if instant is None:
            return None
        if legacy_zone == 'UTC':
            result = calendar.timegm(instant.timetuple())
        else:
            result = int(time.mktime(instant.timetuple()))
            if datetime.datetime.fromtimestamp(result) != instant:
                return None
        return result if result > 0 else None
    except (ValueError, OverflowError, OSError):
        return None


def same(first, second, *, first_zone='local', second_zone='local', weekdays=None, parse=None):
    left = epoch(first, legacy_zone=first_zone, weekdays=weekdays, parse=parse)
    return left is not None and left == epoch(second, legacy_zone=second_zone, weekdays=weekdays, parse=parse)


def _pid(value):
    """A positive PID from an int or a decimal string (JSON often stores PIDs as text)."""
    if type(value) is int:
        return value if value > 0 else None
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value) if int(value) > 0 else None
    return None


def _boot_seconds():
    with open('/proc/stat', 'rb') as stat_file:
        for line in stat_file:
            if line.startswith(b'btime '):
                return int(line.split()[1])
    raise OSError('btime missing from /proc/stat')


def _proc_fields(pid):
    """Fields after the command name of /proc/PID/stat; field 3 (state) is index 0."""
    with open(f'/proc/{pid}/stat', 'rb') as stat_file:
        data = stat_file.read()
    return data[data.rindex(b')') + 2:].split()


def _proc_birth(fields, boot):
    """Same arithmetic as procps `lstart`: boot second + start ticks // ticks per second."""
    birth = boot + int(fields[19]) // os.sysconf('SC_CLK_TCK')
    return birth if birth > 0 else None


def _windows_birth(pid):
    """Creation time from GetProcessTimes, floored to a Unix second like `ps lstart`."""
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *(ctypes.byref(item) for item in times)):
            return None
        ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        birth = ticks // 10_000_000 - 11_644_473_600
        return birth if birth > 0 else None
    finally:
        kernel32.CloseHandle(handle)


def read(pid, *, weekdays=None, parse=None):
    """Birth second of a live process, or None when it is gone or unreadable.

    POSIX reads `ps -o lstart` in the C locale and UTC. Without a `ps` binary
    (minimal containers) Linux falls back to /proc with the same arithmetic;
    Windows reads the creation time from GetProcessTimes.
    """
    pid = _pid(pid)
    if pid is None:
        return None
    if os.name == 'nt':
        return _windows_birth(pid)
    try:
        row = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart='],
                             capture_output=True, text=True, timeout=2, env=PS_ENV)
    except FileNotFoundError:
        try:
            return _proc_birth(_proc_fields(pid), _boot_seconds())
        except (OSError, ValueError, IndexError):
            return None
    except (OSError, subprocess.TimeoutExpired):
        return None
    if row.returncode != 0:
        return None
    return epoch(row.stdout, legacy_zone='UTC', weekdays=weekdays, parse=parse)


def target_text(value, *, weekdays=None, render=None):
    """Render saved address text in the C/local `ps` shape older versions hash.

    Saved text is opaque address material, never an identity value: a string that
    is not a bare integer is returned unchanged. New epochs render the C/local
    `ps` format, including the space-padded day. Pass `render(epoch_seconds)` to
    emit another shape; it must return a non-empty string.
    """
    if isinstance(value, str) and not (value.isascii() and value.isdigit()):
        return value
    birth = epoch(value, weekdays=weekdays)
    if birth is None:
        return ''
    if render is not None:
        rendered = render(birth)
        return rendered if isinstance(rendered, str) else ''
    t = time.localtime(birth)
    return (f'{WEEKDAYS[t.tm_wday]} {list(MONTHS)[t.tm_mon - 1]} {t.tm_mday:2d} '
            f'{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d} {t.tm_year}')


def snapshot(*, weekdays=None, parse=None):
    """One C/UTC observation: pid -> (birth epoch, parent pid).

    POSIX uses `ps -axo`; Linux without `ps` scans /proc. Windows raises OSError:
    there is no single-call snapshot there, read one PID with `read()`.
    """
    if os.name == 'nt':
        raise OSError('process snapshot is not available on Windows; use read(pid)')
    try:
        result = subprocess.run(['ps', '-axo', 'pid=,ppid=,lstart='],
                                capture_output=True, text=True, timeout=5, env=PS_ENV)
    except FileNotFoundError:
        if not os.path.isdir('/proc'):
            raise OSError('process snapshot unavailable: no ps and no /proc') from None
        return _proc_snapshot()
    if result.returncode:
        raise OSError('process snapshot unavailable')
    rows = {}
    for line in result.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        birth = epoch(parts[2], legacy_zone='UTC', weekdays=weekdays, parse=parse)
        if birth is not None:
            rows[int(parts[0])] = (birth, int(parts[1]))
    return rows


def _proc_snapshot():
    boot = _boot_seconds()
    rows = {}
    for name in os.listdir('/proc'):
        if not name.isdigit():
            continue
        try:
            fields = _proc_fields(name)
            birth = _proc_birth(fields, boot)
        except (OSError, ValueError, IndexError):
            continue  # the process exited between listdir and open
        if birth is not None:
            rows[int(name)] = (birth, int(fields[1]))
    return rows


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        raise SystemExit('usage: process_birth.py snapshot|read PID|epoch TEXT [local|UTC]|'\
                         'same A B|target-text TEXT')
    if sys.argv[1] == 'snapshot':
        for pid, (birth, parent) in snapshot().items():
            print(pid, birth, parent)
        sys.exit(0)
    if sys.argv[1] == 'target-text':
        value = target_text(sys.argv[2])
        if not value:
            sys.exit(1)
        print(value)
        sys.exit(0)
    if sys.argv[1] == 'same':
        sys.exit(0 if same(sys.argv[2], sys.argv[3]) else 1)
    value = read(sys.argv[2]) if sys.argv[1] == 'read' else epoch(
        sys.argv[2], legacy_zone=sys.argv[3] if len(sys.argv) > 3 else 'local')
    if value is None:
        sys.exit(1)
    print(value)

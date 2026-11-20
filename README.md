<div align="center">

<img src="https://raw.githubusercontent.com/elfenomenokim/process-birth/main/docs/logo.svg" width="96" height="96" alt="process-birth: two observations of one process collapse to one instant">

# process-birth

A Python module that turns a process start time into one UTC second value, so a reused PID is never mistaken for the same process.

[한국어](README.ko.md) · Python 3.9+

[![pypi](https://img.shields.io/pypi/v/process-birth?label=pypi)](https://pypi.org/project/process-birth/)
[![tests](https://github.com/elfenomenokim/process-birth/actions/workflows/tests.yml/badge.svg)](https://github.com/elfenomenokim/process-birth/actions/workflows/tests.yml)
[![license](https://img.shields.io/github/license/elfenomenokim/process-birth)](LICENSE)

[Install](#install) · [Quick start](#quick-start) · [Why](#why) · [Reference](#reference)

</div>

Parsing one `ps` line costs 3.5 µs minimum and 3.9 µs median; one `ps -axo` snapshot of 1077 processes took 51 ms. Both values are saved in `docs/bench/identity.json`.

A PID is not an identity. The operating system reuses it, so a saved `1234` can point at your editor today and a build worker tomorrow. This module reduces a process to one integer: the Unix second at which it started, normalised to UTC. Two observations of the same process compare equal; two observations with the same PID but different start times do not.

One file, standard library only, so it can be dropped into a remote bundle and executed directly.

## Install

```sh
pip install process-birth
```

Python 3.9+. No dependencies. Verified on macOS arm64 with Python 3.12.

## Quick start

```python
import process_birth

start = process_birth.epoch("Sat Sep 26 11:54:39 2026", legacy_zone="UTC")
print(start)                                   # 1790423679

print(process_birth.read(1) is not None)       # True: pid 1 exists here
print(process_birth.same(start, start))        # True
print(process_birth.same(None, None))          # False: two missing values never match
```

Comparing a saved value with a live process is the point:

```python
import process_birth

saved = 1790423679                  # recorded when the pane was opened
if process_birth.same(saved, process_birth.read(1234)):
    print("same process still owns pid 1234")
else:
    print("pid 1234 is gone, or a different process took it")
```

One snapshot for many comparisons, so you call `ps` once:

```python
import process_birth

rows = process_birth.snapshot()      # {pid: (birth_epoch, parent_pid)}
for pid, (birth, parent) in rows.items():
    if birth > 1790423679:
        print(f"pid {pid} (parent {parent}) started after the saved process")
```

## Why

Process supervision code that matches on a PID has a race with the operating system. Between reading a pane's PID and signalling it, the process can exit and the number can be reused. The signal then reaches an innocent process.

Three properties avoid the usual half-fixes:

- **One integer, not a string.** `ps` output differs by locale, by `LC_ALL`, and between GNU and BSD. Parsing it to a single UTC second makes comparison a number comparison, and removes the timezone question entirely.
- **Missing is never equal.** `same(None, None)` is `False`. Two failed reads are two unknowns, not evidence that both refer to the same process. Code that treats "both empty" as a match is how a deleted pane and a brand-new pane get confused.
- **Real weekdays are checked.** A `ps` line carries a weekday name; the parser cross-checks it against the actual date and rejects the line when they disagree, which catches truncated or shifted output instead of accepting it.

The saved address text (`target_text`) is deliberately separate. It is opaque hash material used to address a terminal endpoint, not an identity value, and its shape is kept stable for values written by older versions.

## Reference

### `epoch(value, *, legacy_zone="local", weekdays=None, parse=None)`

Returns the Unix second for a start time, or `None` when the value is unknown, invalid, or not a real date.

| Input | Result |
| --- | --- |
| Positive `int` | itself |
| Digit string | the integer, or `None` for zero and below |
| `Sat Sep 26 11:54:39 2026` | epoch seconds for that instant |
| `2026년 9월 26일 토요일 11시 54분 39초` | same instant, Korean `ps` shape |
| Mismatched weekday | `None` |
| Anything else | `None` |

`legacy_zone` is `"UTC"` or `"local"`. A value read from `ps` is UTC; `"local"` exists for saved values written before the switch and round-trips through the local clock.

### `read(pid, *, weekdays=None, parse=None)`

Runs `ps -p <pid> -o lstart=` under `LC_ALL=C` and `TZ=UTC`, and returns the birth second, or `None` for an unusable pid or a failed call.

### `same(first, second, *, first_zone="local", second_zone="local", weekdays=None, parse=None)`

True only when both values parse and the seconds are equal.

### `snapshot(*, weekdays=None, parse=None)`

One `ps -axo pid=,ppid=,lstart=` call, returned as `{pid: (birth_epoch, parent_pid)}`. Rows it cannot parse are skipped.

### `target_text(value, *, weekdays=None, render=None)`

Renders saved address text in the C/local `ps` shape (`Sat Sep 26 20:54:39 2026`). A string that is not a bare integer is returned unchanged, because saved text is opaque address material. Pass `render(epoch_seconds)` for another shape.

### Other `ps` locales

```python
FRENCH = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]

def parse_french(text):
    # return (year, month, day, weekday_name, hour, minute, second) or None
    ...

process_birth.epoch("sam 26 sept. 2026 11:54:39",
                    legacy_zone="UTC", weekdays=FRENCH, parse=parse_french)
```

`weekdays` is seven names, Monday first. `parse` is called only when no built-in format matches; return `(year, month, day, weekday_or_None, hour, minute, second)`.

### Command line

```sh
python3 process_birth.py snapshot
python3 process_birth.py read PID
python3 process_birth.py epoch "Sat Sep 26 11:54:39 2026" UTC
python3 process_birth.py same A B
python3 process_birth.py target-text 1790423679
```

Exit status 1 when the value is unknown or the two values differ.

## Numbers

Measured on 2026-11-19 on macOS arm64 (M5 Pro), Python 3.12.8, from `docs/bench/identity.json`.

| What | Result |
| --- | --- |
| `epoch()` on a C-format `ps` line | 3.46 µs min, 3.92 µs median (2000 runs) |
| `snapshot()` on a live host | 1077 rows in 51 ms |
| `epoch("not a date")`, `read(-1)` | `None`, `None` |
| `same(None, None)` | `False` |

## Limits

- **Our runtime keeps a byte-identical copy.** `host/process_birth.py` in the `feno-remote` product must stay a
  real file with the same bytes, because its release bundler reads host modules as Git blobs and a symlink
  would ship the link text. Changing this module means copying it over that file in the same commit.
- **Where the time comes from.** macOS, Linux and the BSDs read `ps -o lstart` in the C locale and UTC. Linux without a `ps` binary (minimal containers) reads `/proc/<pid>/stat` field 22 with the same arithmetic as procps, so both paths give the same second. Windows `read()` uses the process creation time from GetProcessTimes; `snapshot()` raises `OSError` on Windows.
- **One-second resolution.** Two processes started inside the same second are indistinguishable. That is the resolution `ps` reports.
- **No privilege check.** Anyone who can read the process can read its start time. This is not an authentication mechanism.
- **Weekday cross-check assumes a real calendar date.** A `ps` output with a fabricated weekday is rejected, by design.
- **Verified** by the test suite on macOS, Ubuntu and Windows. On Ubuntu 24.04 the `/proc` path and `ps` agreed on all 222 live processes. Only the macOS `ps` was timed.
- **Daylight-saving fold.** `epoch(text, legacy_zone="local")` for a repeated local hour (the autumn change) picks one of the two instants. Live reads are unaffected: `read()` and `snapshot()` always ask `ps` for UTC.

## FAQ

**Why UTC seconds instead of a timestamp string?** A string comparison depends on locale, spacing and timezone. After parsing to one integer, the timezone question disappears and a stale value cannot look equal because both were rendered the same way.

**Why is `same(None, None)` false?** Because two failed reads are two unknowns. Treating them as a match is how a dead pane and a fresh pane in the same slot get confused.

**Is `target_text` an identity?** No. It is opaque address material whose shape must stay stable for saved values. Use `epoch()` and `same()` for identity.

## Contributing

Bug reports and patches are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the fixture each behaviour change needs.

## Licence

MIT, in [LICENSE](LICENSE).

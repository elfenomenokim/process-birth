# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-20

### Added

- Windows: `read()` returns the creation second from GetProcessTimes. `snapshot()` raises
  `OSError` there instead of failing to find `ps`.
- Linux without `ps`: `read()` and `snapshot()` fall back to `/proc` with the procps
  arithmetic, so the values match `ps -o lstart`.
- `read()` accepts a decimal string PID (`"123"`), as JSON often stores it; booleans
  stay rejected.
- A test suite and the tests workflow on Ubuntu, macOS and Windows.

### Fixed

- `docs/bench/identity.py` no longer rewrites the committed measurement unless run
  with `--write`.
- The package no longer claims "OS Independent"; it lists macOS, Linux and Windows.

## [0.1.0] - 2026-11-19

### Notes

- `feno-remote/host/process_birth.py` stays a byte-identical copy of this file. The release bundler reads host
  modules as Git blobs, so a symlink there would ship the link text instead of the module.

### Added

- `epoch(value, legacy_zone=..., weekdays=None, parse=None)` reduces a `ps` start time, a saved epoch or a
  Korean-locale `ps` line to one UTC second, rejecting a line whose weekday contradicts its date.
- `read(pid)` runs one `ps -p` call under `LC_ALL=C` and `TZ=UTC`; `snapshot()` reads every process in one
  call as `{pid: (birth_epoch, parent_pid)}`.
- `same(first, second)` is true only when both values parse and match; two missing values never match.
- `target_text(value, render=None)` keeps the saved address text shape stable for older values, and can
  render another shape.
- Weekday names and extra date formats are caller arguments (`weekdays=`, `parse=`) instead of a Korean-locale
  assumption, so another `ps` locale is configured rather than patched.
- The module stays one standard-library file, so it can be dropped into a bundle and executed directly.

[Unreleased]: https://github.com/elfenomenokim/process-birth/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/elfenomenokim/process-birth/releases/tag/v0.1.0

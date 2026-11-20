# AGENTS.md

## Layout

- `process_birth.py`: the whole module — parsing, the `ps` calls, comparison, and the CLI entry point.
- `docs/bench/identity.py`: re-measures parse cost and snapshot size, rewriting `docs/bench/identity.json`.
- `docs/logo.svg`: the mark used in the README.
- `public.json`: export allowlist and repository metadata.

## Commands

Run from the repository root:

```sh
python3 -m compileall -q process_birth.py
python3 process_birth.py epoch "Sat Sep 26 11:54:39 2026" UTC
python3 process_birth.py read $$
python3 docs/bench/identity.py
```

There is no test runner. Use literal `ps` lines captured under `LC_ALL=C TZ=UTC` as fixtures.

## Changes

- Keep this a single file with standard-library imports only. It is copied into remote bundles and executed
  directly; a relative import or a second module breaks them.
- Identity is one integer: UTC seconds. Do not add a second comparable representation.
- Unknown, invalid or unparsable input returns `None`. `same()` of two non-values is `False`.
- Keep the weekday cross-check. It rejects truncated or shifted `ps` output that would otherwise parse.
- `target_text` keeps its output shape for values written by older versions; it is address material, not
  identity. Additions go through its `render=` argument.
- Fix the `ps` invocations to `['ps', ...]` with `LC_ALL=C` and `TZ=UTC`. Never build a shell string.
- Locale behaviour is an argument (`weekdays=`, `parse=`), never a new built-in hard-coded format.
- Keep README.md, README.ko.md, the `pyproject.toml` description and `public.json` aligned.
- A local commit is not publication. Version bumps and PyPI uploads need the maintainer's instruction.

## The vendored copy in the host tree

`docs/products/feno-remote/host/process_birth.py` is a byte-identical copy of `process_birth.py` here. It
cannot be a symlink or an import: the release bundler reads each host module as a Git blob
(`git show <rev>:<path>`) and execs it inside the remote bundle, and `git show` returns the link text for a
symlink. When you change this file, copy it over the host copy in the same commit:

```sh
cp process_birth.py ../host/process_birth.py
```

## Hard don'ts

- Do not treat two missing observations as equal.
- Do not accept a line whose weekday contradicts its date.
- Do not let a caller-supplied value reach a shell.
- Do not return a float, a `datetime`, or a formatted string from `epoch()`.

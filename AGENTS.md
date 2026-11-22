# AGENTS.md

## Set up for a user

Goal: the user's Python project can `import process_birth` and compare a saved process start time with a live process. This is a single-file library; "working" means the check below runs with the project's own interpreter. macOS and Linux (it calls `ps`).

1. Check what is present.
   - Find the project (the folder with `pyproject.toml` or `requirements.txt`); if the user did not say which, ask: "어느 프로젝트에 넣을까요? 폴더 위치를 알려주세요." Do not install into the system Python.
   - `uv --version` prints a version. If not: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `export PATH="$HOME/.local/bin:$PATH"`.
   - The project's interpreter is Python 3.9 or newer; no venv yet: `uv venv` in the project folder.
   - `ps -axo pid=,lstart= | head -1` prints a row.
2. Install into the project: `uv add process-birth` (uv-managed project), or `uv pip install process-birth` (plain venv). No dependencies. A remote bundle that must stay one file can instead copy `process_birth.py` from the repository.
3. Nothing here needs the person.
4. Prove it, with the project's interpreter:
   ```sh
   python -c "import process_birth as p; s = p.epoch('Sat Sep 26 11:54:39 2026', legacy_zone='UTC'); print(s, p.read(1) is not None, p.same(s, s), p.same(None, None))"
   ```
   Success prints `1790423679 True True False`.
5. If it fails, in this order:
   - `externally-managed-environment` from pip: you used the system Python; use the project's venv.
   - `ModuleNotFoundError: process_birth`: the check ran with a different interpreter than the install.
   - `read(1)` is `None` (second value `False`): `ps` is missing or blocked (a minimal container without procps, or a sandbox); install `procps` or report the `ps` error.
   - Windows: not supported.

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

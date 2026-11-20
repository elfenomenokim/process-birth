# Contributing to process-birth

Bug reports and patches are welcome. You do not need to ask before opening a pull request for a bug fix.

## Before you start

- **A parse returned the wrong second, or accepted a bad line:** open an issue with the exact `ps` output
  line, your `ps` flavour (`ps --version`, or the platform), the timezone, and what you expected.
- **A change to the "missing is never equal" rule:** open an issue first. Process supervision depends on it.
- **A security problem:** do not open a public issue. See [SECURITY.md](SECURITY.md).

## Set up

```sh
git clone https://github.com/elfenomenokim/process-birth
cd process-birth
python3 -m compileall -q process_birth.py
python3 process_birth.py epoch "Sat Sep 26 11:54:39 2026" UTC
python3 process_birth.py read $$
python3 docs/bench/identity.py
```

There is no separate test runner. Exercise a change with literal `ps` lines captured under
`LC_ALL=C TZ=UTC`, never with a live process you do not own.

## Rules a patch must keep

- The module stays a single file with standard-library imports only. It is copied into remote bundles and
  executed directly, so a relative import or a second module breaks every bundle.
- One identity value: integer UTC seconds. Do not add a second comparable representation.
- An unknown, invalid or unparsable value is `None`, and `same()` of two non-values is `False`.
- The weekday cross-check stays. Rejecting a line whose weekday contradicts its date is the guard against
  truncated or shifted `ps` output.
- `target_text` output shape stays stable for values written by older versions. It is opaque address
  material, not an identity.
- Locale differences are arguments (`weekdays=`, `parse=`), never a new hard-coded format.
- Keep README.md, README.ko.md, the `pyproject.toml` description and `public.json` aligned.
- A local commit is not publication. Version bumps and PyPI uploads need the maintainer's instruction.

## What a good patch has

- **A literal `ps` line** that fails before the change and parses after it, plus the expected second.
- **A line under Unreleased** in [CHANGELOG.md](CHANGELOG.md) when a caller will notice.
- **The platforms you did not test** written in the pull request. Only macOS has been exercised.

## Licence

Contributions are licensed under the MIT licence in [LICENSE](LICENSE).

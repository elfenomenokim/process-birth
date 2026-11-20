# Security policy

## Supported versions

Security fixes go into the latest release. Upgrade before reporting, in case the problem is
already fixed.

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| Older | No |

## Reporting a vulnerability

Report it privately, not in a public issue: use the
[Report a vulnerability](https://github.com/elfenomenokim/process-birth/security/advisories/new)
form on the repository's Security tab.

Include the `ps` line or platform, the version, and what an attacker could do with the result. You get a
reply within a few days.

## In scope

- A value that parses successfully but describes a different instant, for example through a timezone or
  weekday cross-check bypass.
- Two different processes comparing equal.
- A crafted `ps`-shaped string that makes the parser raise instead of returning `None`.
- A `pid` argument that makes the module run something other than the fixed `ps` command.
- A `parse` callback result that leads to writing outside the module's own state.

## Not a vulnerability

- Two processes started in the same second comparing equal. That is the resolution `ps` reports.
- Reading another user's process start time when you can already list processes. This is not authentication.
- `same(None, None)` being `False`. That is the documented rule.
- A rejected line whose weekday does not match its date.

## Disclosure

Once a fix is released, the advisory is published with credit to the reporter unless they prefer
otherwise.

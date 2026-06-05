# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-06-05

First public release. Verified end-to-end against the live Satchel One API with a
real parent account.

### Features
- **Config-flow setup** (no YAML): search for your school by name → pick your
  school → enter parent email + password → optionally link each child to an
  existing `person.*` entity.
- **Per-child device** with sensors: homework due count, next homework due,
  behaviour credits, demerits (`unknown` for positive-only schools), conduct net,
  and upcoming detentions.
- **Binary sensors**: overdue homework, detention today.
- **Events** for automations: `satchel_one_new_homework`, `satchel_one_credit`,
  `satchel_one_demerit` — each carrying the linked `person` and (for behaviour)
  a `severity` = `abs(points)`. Seen-ID persistence avoids event storms on
  restart.
- **Options flow**: configurable homework/behaviour poll intervals (5-minute
  floor) and child→person re-mapping.
- **Reauth** flow and **redacted diagnostics**.

### Notes on the API
- Authenticates via the OAuth2 password grant at `/oauth/token` (root, not under
  `/api`) using the public web client credentials, scoped to a `school_id`
  resolved from a school search.
- All requests use the versioned `application/smhw.v2021.5+json` Accept header.
- Uses an **unofficial, reverse-engineered** API; it may break if Satchel One
  changes their service.

### Not yet implemented
- **Attendance** — endpoint not yet captured from live traffic.
- **Silent token refresh** — reauth currently re-prompts for the password.

[1.0.0]: https://github.com/wheezer256/satchel-one/releases/tag/v1.0.0

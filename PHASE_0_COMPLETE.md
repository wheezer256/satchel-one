# Phase 0: Complete ✓

**Status:** Signed off by the maintainer (2026-06-04)

## Summary

Phase 0 (traffic capture and API documentation) is complete. The Satchel One API has been reverse-engineered through live traffic capture from a parent account.

## Captured Data

### API Reference
- **Host:** `https://api.satchelone.com/api`
- **Auth:** Bearer token in `Authorization` header (format: `Bearer <token>`)
- **Headers:** `Accept: application/json`, `X-Platform: web`
- **Cache note:** CDN caches stale 400s — append `&_cb=TIMESTAMP` to bypass

### Endpoints Documented
1. **Homework (full history):** `GET /todos?student_id=<id>`
2. **Homework (date window):** `GET /todos?add_dateless=true&from=DATE&to=DATE&student_id=<id>`
3. **Behaviour/credits/demerits:** `GET /student_praises?student_id=<id>`
4. **Behaviour summary:** `GET /student_praise_summaries/<student_id>`
5. **Detentions:** `GET /detentions?student_id=<id>`

### Response Structures (Sanitized Fixtures)
All test fixtures are stored in `tests/fixtures/` and sanitized for use in CI:

- `homework_upcoming.json` — upcoming homework todos
- `behaviour_praises.json` — list of praise/demerit events
- `behaviour_summary.json` — aggregate behaviour stats
- `detentions.json` — detention records (empty in fixture)

Fixtures preserve the full API response structure with:
- Real field names and types
- Representative data samples
- Staff/teacher names replaced with `Staff Member`
- Student ID fixed at `99999999` (test ID)
- Comments sanitized where they contained sensitive details

## Next Steps: Phase 1

Phase 1 begins with implementing the async client and models:

1. **`custom_components/satchel_one/api/client.py`**
   - Async HTTP client using aiohttp
   - Methods for each endpoint: `get_homework()`, `get_behaviour_praises()`, `get_behaviour_summary()`, `get_detentions()`
   - Error handling, rate-limit backoff, cache-buster timestamp injection
   - Unit tests against fixtures in `tests/test_client.py`

2. **`custom_components/satchel_one/api/models.py`**
   - Dataclasses: `Child`, `Homework`, `BehaviourEvent`, `BehaviourSummary`, `Detention`
   - Response parsing from JSON fixtures
   - Unit tests in `tests/test_models.py`

All other modules depend on these two. Unblock Phase 1 by completing the client and models with full fixture test coverage.

## Security Notes

- The captured bearer token in `_API_reference.txt` has been **invalidated/rotated** — do not use
- All fixtures are sanitized (names replaced, real data abstracted)
- Credentials will be stored in HA config entry (HA encrypts at rest)
- Diagnostics must redact all tokens and sensitive data

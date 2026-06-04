# Spec: Satchel One → Home Assistant Integration

**Domain:** `satchel_one`
**Type:** Home Assistant custom component (HACS-distributable)
**Author of spec:** the maintainer
**Audience:** Claude Code

---

## 1. Goal

Surface, **per child**, the following from Satchel One into Home Assistant:

- Homework / to-do assignments (outstanding, due-soon, overdue, submission state)
- **Credits** (positive behaviour / praise points)
- **Demerits** (negative behaviour points)
- Supporting context that's cheap to pull alongside: detentions, attendance, notifications

Each child must be **linkable to an existing `person` entity** so downstream automations (push notifications, screen-time enforcement, etc.) can target the right human. The integration's job ends at *exposing clean state + events*; enforcement (e.g. blocking a device via the existing UniFi integration, calling a notify service) lives in user automations, not in this component.

---

## 2. Hard constraints (read before designing anything)

1. **There is no official/public Satchel One API.** This integration rides the same unofficial REST API the mobile/web clients use, which the community has reverse-engineered. Treat every endpoint as undocumented and subject to change.
2. **Async only.** This runs inside Home Assistant's event loop. Use `aiohttp` via `homeassistant.helpers.aiohttp_client.async_get_clientsession`. **Do not** copy the reference libraries' blocking `httpx`/`requests` calls into the runtime path — study them for endpoint shapes, reimplement async.
3. **Config-flow based, no YAML config.** `config_flow: true`, `iot_class: cloud_polling`.
4. **Parent account, multiple children.** The reverse-engineered docs are *student-account* centric. You are authenticating as a **parent** with N children. The child-data access path is the single biggest unknown — see Phase 0.
5. **Be a polite client.** No documented rate limits → be conservative, back off on 429/5xx, single shared session, reasonable poll interval.
6. **Unofficial = fragile.** Isolate *all* HTTP interaction behind one thin client module so a broken endpoint is a one-file fix.

---

## 3. Phase 0 — Discovery spike (DO THIS FIRST, do not skip)

The published community docs describe student logins. Before writing the integration, **capture real traffic from the maintainer's own parent account** to pin down the actual request/response shapes. Without this, the data model will be guesswork.

**Method:** proxy the Satchel One mobile app or web session (mitmproxy / Charles, or browser devtools → Network for the web client) while logged in as the parent.

**Capture and record (into `docs/api-capture.md`):**

- The exact **OAuth token request**: URL, the current `client_id` / `client_secret` in use, grant type, form fields, and the full token response (`access_token`/`smhw_token`, `refresh_token`, `expires_in`, `user_id`, `school_id`, `user_type`).
  - *Note:* historical hardcoded web + mobile client credentials are published in the `fourohfour` gist (see §4), but they may have rotated. **Re-confirm from live traffic** rather than trusting the gist.
- The **`Accept` header** value the client sends (historically `application/smhw.v3+json` — confirm the current version).
- The **`Authorization`** scheme (historically `Bearer {smhw_token}`).
- **How a parent enumerates children**: which endpoint returns the list of student records tied to the parent (look for a `children`, `students`, or parent-user record with child IDs).
- For **one child**, capture the full request/response for: to-do/homework list, a single homework/task detail, behaviour points (positive *and* negative), detentions, attendance, notifications. Record which query param scopes the request to a child (`student_id`? path segment? separate child token?).
- Note any **`User-Agent` / `X-*` headers** the real client sends — we'll mimic these to reduce the chance of being flagged as a non-official client (the Python reference lib explicitly warns it does *not* fully mimic the official clients).

**Exit criterion:** a documented, working `curl`/HTTPie sequence that logs in as the parent and pulls homework + behaviour for a named child. Everything after this builds on that.

---

## 4. Upstream API summary (grounded reference, verify in Phase 0)

Base host historically `api.showmyhomework.co.uk`, now `api.satchelone.com`. Confirm live.

**Auth:** OAuth2 password grant.
- `POST /oauth/token` with `client_id`, `client_secret`, `grant_type=password`, `username`, `password`.
- Response carries a bearer-type token plus an `smhw_token` (the one historically used in the `Authorization` header), a `refresh_token`, `expires_in`, and identity fields (`user_id`, `school_id`, `user_type`).
- Refresh via `grant_type=refresh_token` before expiry.
- A **school lookup** is required to resolve a `school_id`/subdomain from the school name before login.

**Request convention:** `GET https://{host}/api/{resource}?{params}` with header `Accept: application/smhw.v{N}+json` and `Authorization: Bearer {smhw_token}`. Omitting the `Accept` version header historically returned a generic 404 page instead of JSON.

**Resources confirmed to exist** (from the Python reference lib's feature list — map exact paths in Phase 0):
- to-do list / tasks (homework), single task detail, task search
- **behaviour: praise points and behaviour points** (→ credits / demerits)
- detentions, attendance
- the user's own data, the user's **parents** data, employee/teacher data
- per-user and whole-school calendar
- notifications

**Terminology caution:** schools configure their own behaviour vocabulary — "merits/demerits", "credits", "praise/behaviour points", "achievement/negative points". Don't hardcode "credit"/"demerit". Derive **polarity** (positive = credit, negative = demerit) from the point value and surface the school's own labels where present. Schools with **"positive only behaviour"** hide negative points from parents/students — handle the demerit channel being absent gracefully.

**Behaviour point scale (TO VERIFY in Phase 0):** each behaviour event appears to carry a signed score on a small bounded scale, roughly **−4 to +4**, where the **sign is polarity** (negative = demerit, positive = credit) and the **magnitude is severity/significance**. Treat each event as `(polarity, magnitude)` rather than a single tally count. Things to confirm: the exact range and whether it includes 0; whether the scale is fixed by Satchel or **school-configurable** (so don't hardcode ±4 — capture the observed min/max but keep the model open to other ranges); and whether the scored value and a human-readable category/label are separate fields.

**Reference implementations (study, don't vendor the sync HTTP):**
- `EpicGamerCodes/smhw-api` (a.k.a. `bevynfernandes/smhw-api`) — Python 3.11, type-hinted response objects in `src/smhw_api/objects.py`. **Best source for response schemas.** Note the `dev` branch.
- `edqx/node-smhw` / `node-smhw-client` — Node, broad endpoint coverage, JSDoc.
- `fourohfour` gist `ccb010776c8a8157f597501bb55fde66` — original auth/endpoint write-up + historical client credentials.

---

## 5. Architecture

Standard HA custom component layout:

```
custom_components/satchel_one/
  __init__.py            # setup/unload, coordinator wiring
  manifest.json          # domain, version, requirements, config_flow, iot_class=cloud_polling
  api/
    client.py            # ALL HTTP lives here. aiohttp. login, refresh, typed fetch methods
    models.py            # dataclasses for Child, Homework, BehaviourEvent, Detention, etc.
    const_api.py         # host, accept header version, client_id/secret, endpoint paths
  config_flow.py         # school search → parent creds → child→person mapping (options)
  coordinator.py         # DataUpdateCoordinator(s), delta detection → event firing
  const.py               # DOMAIN, defaults, event names, attribute keys
  sensor.py
  binary_sensor.py
  diagnostics.py         # redacted dump for debugging
  strings.json / translations/en.json
```

**Client module (`api/client.py`)** is the only place that knows about Satchel's HTTP. It exposes async methods returning typed models: `async login()`, `async refresh()`, `async get_children()`, `async get_homework(child_id)`, `async get_behaviour(child_id)`, `async get_detentions(child_id)`, etc. On `401`, transparently refresh once and retry; on refresh failure, raise an auth error that triggers HA reauth.

---

## 6. Data model & entities

**One HA Device per child** (via `DeviceInfo`, `identifiers={(DOMAIN, child_id)}`, name = child's name, manufacturer "Satchel One"). All of that child's entities attach to this device. This keeps the dashboard clean and makes the child the natural automation target.

### Sensors (per child)

| Entity | State | Key attributes |
|---|---|---|
| `sensor.<child>_homework_due` | count of outstanding tasks | list of tasks: title, subject, teacher, set_date, due_date, submission_required, submission_status, task_id, url |
| `sensor.<child>_next_homework` | timestamp/title of next due | the full next task object |
| `sensor.<child>_credits` | running total of positive points | recent positive events: points (signed, magnitude = severity), reason/category, subject, teacher, timestamp |
| `sensor.<child>_demerits` | running total of negative points | recent negative events (same shape); absent/`unknown` if school is positive-only |
| `sensor.<child>_conduct_net` | credits − demerits (signed point sum) | today_delta, week_delta, worst_today (most negative single event), best_today (most positive single event) |
| `sensor.<child>_detentions` | count upcoming | list: date, time, location, reason |

Use `device_class`/`state_class` where meaningful (totals → `total_increasing` is risky if points can be revoked; prefer `measurement`). `next_homework` → `device_class: timestamp`.

### Binary sensors (per child)

- `binary_sensor.<child>_overdue_homework` — on when any task is past due and unsubmitted.
- `binary_sensor.<child>_detention_today` — on when a detention is scheduled today.

**Every child entity carries a `linked_person` attribute** (the mapped `person.*` entity_id, or `None`) so templates/automations can resolve the human directly from the entity.

---

## 7. Person linking

HA does not let a device be "owned" by a `person`, so model the link explicitly:

- In the **options flow**, for each discovered child, present a selector of existing `person` entities (plus "none"). Store as `entry.options["child_person_map"] = {child_id: "person.alice"}`.
- Apply the mapping in two places:
  1. `linked_person` attribute on every child entity (§6).
  2. `person` field in **every fired event** (§8).

This gives automations a single, stable handle (`person.alice`) regardless of how the child's entities are named, so the same automation blueprint works for every child.

---

## 8. Event model (the important part for automations)

Cumulative sensors are wrong for *transient* things like "a demerit was just issued." The coordinator must **diff each poll against the previous snapshot** and fire HA events for new occurrences. These events are what notifications and screen-time automations trigger on.

Fire on the HA event bus:

- `satchel_one_new_homework` → `{ child_id, child_name, person, task_id, title, subject, teacher, due_date, submission_required }`
- `satchel_one_credit` → `{ child_id, child_name, person, points, severity, reason, subject, teacher, timestamp }`
- `satchel_one_demerit` → `{ child_id, child_name, person, points, severity, reason, subject, teacher, timestamp }`
- `satchel_one_detention` → `{ child_id, child_name, person, date, time, location, reason }`
- `satchel_one_homework_overdue` → `{ child_id, child_name, person, task_id, title, due_date }`

**Delta detection rule:** persist the set of seen IDs (task IDs, behaviour-event IDs, detention IDs) across restarts via the coordinator's stored data / a restore mechanism, so a HA restart doesn't replay every historical item as "new." On the very first successful fetch, seed the seen-sets **silently** (no event storm).

**`points` vs `severity` in behaviour events:** `points` is the raw **signed** value from the API (e.g. −3, +1). `severity` is its **absolute magnitude** (`abs(points)`, e.g. 3, 1), provided as a convenience so automations can branch on seriousness without sign maths — e.g. "notify only if `severity >= 3`" or escalate screen-time enforcement by tier. If Phase 0 reveals a separate human label per tier (e.g. a name for a ±4), include it as `tier_label`.

> Example downstream automation (illustrative, **not** to be built here): `satchel_one_demerit` for `person.alice` → `notify.parents` + a UniFi traffic-rule/client-block service call to throttle her screen time. Given the existing UniFi Dream Machine setup, UniFi is the natural enforcement layer — but that's a user automation, out of scope for this component.

---

## 9. Config flow & options flow

**Config flow (initial setup):**
1. **School step** — text input for school name/subdomain → call the school-lookup endpoint → present matches → user selects → store `school_id`.
2. **Credentials step** — parent username + password → attempt login → on success store tokens; on failure show `invalid_auth`.
3. Create the entry; trigger child discovery.

**Reauth flow** — when refresh fails / credentials change, prompt for password again (school + username preserved).

**Options flow:**
- Child → person mapping (§7).
- Poll interval (default per §10).
- Toggles for which channels to enable (homework / behaviour / detentions / attendance) so users on positive-only or homework-disabled schools aren't spammed with `unknown` entities.
- Display label overrides for credit/demerit naming.

---

## 10. Coordinator & polling

- Use `DataUpdateCoordinator`. Consider **two** coordinators with different intervals: homework changes slowly (default **30 min**), behaviour/detentions arguably want fresher polling (default **15 min**) for timely notifications. Both user-configurable; floor at something polite (e.g. 5 min).
- One shared `aiohttp` session. Prefer HTTP/2 if the host supports it.
- A single login/token is shared across all children's fetches.
- Fan out per-child fetches with bounded concurrency (e.g. `asyncio.gather` but cap if a parent has many children).
- Back off on `429`/`5xx` with jitter; surface persistent failure as coordinator `UpdateFailed` (entities go `unavailable`, don't crash).

---

## 11. Resilience & error handling

- All endpoint paths, the host, and the `Accept` version live in `const_api.py` — single point of repair.
- `401` → refresh-and-retry-once → else reauth.
- Missing module (behaviour disabled, positive-only, homework disabled): catch the specific failure, mark that channel unavailable, keep the rest working. Don't fail the whole entry.
- Defensive parsing: the API may add/rename fields. Parse into models tolerantly (unknown fields ignored, missing optional fields default), and log at debug with the raw payload behind a flag.
- `diagnostics.py` must dump config + last payloads with **credentials, tokens, and child PII redacted**.

---

## 12. Security

- Store username/password and tokens in the config entry (HA encrypts entries at rest on supervised installs; still treat as sensitive).
- Never log credentials or tokens. Redact in diagnostics and debug logs.
- Children's names/behaviour data are minor PII — keep it inside HA, no external calls beyond Satchel's host.

---

## 13. Testing

- Unit-test the client against **recorded fixtures** from the Phase 0 capture (store sanitized JSON in `tests/fixtures/`). No live API in CI.
- Test delta detection: first-fetch seeding fires nothing; a new behaviour event fires exactly one event; a HA restart with persisted seen-sets fires nothing.
- Test positive-only school (no demerit channel) and homework-disabled school degrade cleanly.
- Test token refresh path and reauth trigger.
- Config-flow tests: school search, bad creds, child→person mapping in options.

---

## 14. Milestones

1. **Phase 0 spike** — traffic capture, documented working curl sequence, sanitized fixtures. *(gate: nothing else starts until this is signed off)*
2. **Client + models** — async login/refresh, `get_children`, `get_homework`, `get_behaviour`; unit-tested against fixtures.
3. **Config flow + single coordinator + homework sensors** — end-to-end for one child, installable via HACS.
4. **Behaviour (credits/demerits) sensors + event firing with delta detection.**
5. **Person mapping (options flow), `linked_person` attribute, `person` in events.**
6. **Detentions, attendance, notifications, binary sensors, second coordinator.**
7. **Diagnostics, reauth, polish, README with example automations (notify + UniFi screen-time as illustrations).**

---

## 15. Out of scope

- Any enforcement (notifications, screen-time, device blocking) — those are user automations downstream of the events/state this component exposes.
- Writing back to Satchel (submitting homework, acknowledging detentions). Read-only.
- Supporting teacher/admin accounts. Parent (and incidentally student) accounts only.

---

## 16. Open questions (resolve during Phase 0 / flag if blocked)

1. Exact parent→child enumeration endpoint and the child-scoping parameter — **the critical unknown.**
2. Current live `client_id`/`client_secret` and `Accept` header version (gist values may be stale).
3. Whether a parent token can fetch all children directly, or whether per-child tokens/sub-requests are needed.
4. Behaviour event schema: does it expose a stable per-event ID (needed for delta detection), a polarity/category field, and the signed score? **Confirm the point scale** — observed ≈ −4 to +4; verify the exact range, whether it's fixed or school-configurable, and whether a tier/label accompanies each magnitude.
5. Whether totals can be *revoked* (affects `state_class` choice for credit/demerit sensors).

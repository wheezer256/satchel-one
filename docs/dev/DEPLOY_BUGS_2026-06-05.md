# Satchel One integration — bug report (verified live 2026-06-05)

**Context:** deployed to live HA. Login + school search + `get_children` now work.
Homework entities populate correctly (`homework_due`, `next_homework`,
`overdue_homework` all live). Remaining bugs below, all confirmed by probing the
real API from inside the HA container with the stored bearer token.

---

## Bug 1 — Wrong `Accept` header on authenticated data calls (causes HTTP 400)

`api/const_api.py` → `DEFAULT_HEADERS` uses `"Accept": "application/json"`.
The API/CDN rejects that with an XML 400:

```xml
<Error><Code>InvalidArgument</Code>
<Message>Unsupported Authorization Type</Message></Error>
```

The versioned vendor type works for **every** data endpoint; plain JSON 400s on
all of them (homework only succeeded earlier by CDN-cache luck):

| Accept header | students | todos | praises | detentions | summary |
|---|---|---|---|---|---|
| `application/json` | 400 | 400 | 400 | 400 | 400 |
| `application/smhw.v2021.5+json` | 200 | 200 | 200 | 200 | 200 |

**Fix:** in `DEFAULT_HEADERS` change
`"Accept": "application/json"` → `"Accept": "application/smhw.v2021.5+json"`
(i.e. use the same versioned Accept that `BASE_HEADERS` already uses for
login/school-search, for the authenticated `_get` calls too).

---

## Bug 2 — Phantom `data` wrapper in behaviour parsing (`KeyError: 'data'`)

Real response bodies are top-level, **not** nested under `data`. Confirmed shapes:

- `/student_praises` → `{"student_praises": [ {id, points, student_id, staff_member_id, kudos_reason_id, description, kudos_event_id, ...} ]}`
- `/detentions` → `{"detentions": [...], "meta": {...}}`
- `/student_praise_summaries/{id}` → `{"student_praise_summary": {total_positive_count, total_negative_count, total_count, week_/month_/day_*_count, ...}}`

**Fix in `api/client.py`:**

```python
# get_behaviour_praises
[BehaviourEvent.from_dict(p) for p in data["data"]["student_praises"]]
→ [BehaviourEvent.from_dict(p) for p in data["student_praises"]]

# get_detentions
[Detention.from_dict(d) for d in data["data"]["detentions"]]
→ [Detention.from_dict(d) for d in data["detentions"]]

# get_behaviour_summary: already correct — data["student_praise_summary"]
```

---

## Bug 3 — `_get()` swallows 4xx into confusing errors (robustness)

`api/client.py` `_get()` only raises on 429 and `>=500`, so 4xx bodies fall
through to `await resp.json()`. That's why Bugs 1 & 2 surfaced as
`KeyError`/`ContentTypeError` instead of a clear message. Add explicit 4xx
handling: raise `AuthError` on 401/403, and a clear error including
`resp.text()` on other 4xx (don't blind-call `.json()`).

---

## Bug 4 — Child→person mapping dropdown shows student IDs, not names

`config_flow.py` `async_step_link_children` builds per-child fields keyed by
`vol.Optional(f"child_{child.id}")`. HA renders the field **label** from the
(untranslated, dynamic) schema key, so the form shows `child_<id>` / the raw
student id instead of the child's name. Same issue in
`SatchelOneOptionsFlow.async_step_init` (line ~284).

**Fix:** key the per-child select by the child's **name** (e.g.
`vol.Optional(child.name)`) and adjust the read-back accordingly, **or** supply a
human-readable field label so the dropdown shows the child's name rather than the
id. Applies to **both** the config flow link step and the options flow.

---

After fixing 1 + 2, behaviour sensors (`_credits` / `_demerits` / `_conduct_net`)
will populate. 3 is hardening. 4 is the mapping UX. Then redeploy.

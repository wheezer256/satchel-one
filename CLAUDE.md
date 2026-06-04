# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains the specification and implementation for a **Home Assistant custom component** (HACS-distributable) that integrates the **Satchel One** school platform. The component surfaces per-child school data—homework, behaviour credits/demerits, detentions, and attendance—from the unofficial Satchel One REST API into Home Assistant entities and events, enabling automations like push notifications or screen-time enforcement.

**Key facts:**
- Language: Python (async-only)
- Framework: Home Assistant custom component architecture
- API: Reverse-engineered, unofficial Satchel One REST API
- Distribution: HACS integration, config-flow only (no YAML config)

## Development Gate: Phase 0 Must Complete First

**No implementation code starts until Phase 0 is complete and signed off.** Phase 0 involves capturing live traffic from the maintainer's parent account to establish:
- Real API endpoints
- Authentication shape (headers, client credentials, bearer tokens)
- Parent → child enumeration and data structure
- Sanitized JSON fixtures for test data

This traffic capture is documented as a curl sequence and feeds into `tests/fixtures/`. Once Phase 0 is signed off, implementation can proceed using these verified fixtures.

## Planned Directory Structure

```
custom_components/satchel_one/
  __init__.py               # setup/unload, coordinator wiring
  manifest.json             # domain metadata, config_flow: true, iot_class: cloud_polling
  api/
    client.py               # ONLY file that makes HTTP calls (aiohttp, async)
    models.py               # typed dataclasses: Child, Homework, BehaviourEvent, Detention…
    const_api.py            # API host, Accept header, client credentials, endpoint paths
  config_flow.py            # school search → parent creds → child→person mapping
  coordinator.py            # DataUpdateCoordinator(s) + delta detection + event firing
  const.py                  # DOMAIN, event names, attribute keys
  sensor.py                 # sensor entities
  binary_sensor.py          # binary sensor entities
  diagnostics.py            # redacted dump for debugging
  strings.json              # translatable strings
  translations/en.json
  tests/
    fixtures/               # sanitized JSON responses from Phase 0 capture
    test_*.py               # pytest tests
```

## Architectural Constraints & Patterns

### HTTP Client Isolation
**Rule:** `api/client.py` is the **sole file** that knows about Satchel's HTTP API. All other modules consume typed models from `api/models.py`. This isolation makes testing and maintenance tractable.

### Two Update Coordinators
The component uses two `DataUpdateCoordinator` instances with different poll intervals:
- **Homework coordinator:** 30 min default (slow-changing data)
- **Behaviour/detention coordinator:** 15 min default (faster, for timely event notifications)

Both intervals are user-configurable via config entry options with a **5-minute floor**—never allow intervals shorter than 5 min to avoid overwhelming the API.

### One Device Per Child
All entities and events for a given child are keyed to a single Home Assistant Device, identified by `(DOMAIN, child_id)`. The device name should reflect the child's name from the API response.

### Person Linking
Children can be linked to existing `person.*` entities in Home Assistant via the options flow. This `linked_person` attribute must appear on every entity and in every fired event to enable downstream automations that care about which child triggered an event.

### Event-Driven Architecture
On each coordinator poll, delta-detect against the previous snapshot and fire Home Assistant bus events:
- `satchel_one_new_homework` — new homework assigned
- `satchel_one_credit` — positive behaviour point awarded
- `satchel_one_demerit` — negative behaviour point awarded
- `satchel_one_detention` — new detention recorded
- `satchel_one_homework_overdue` — homework became overdue

**Seen-ID persistence:** Maintain a persistent set of already-seen homework/detention IDs (stored in HA's persistent storage via `store.async_save()`). This prevents event storms on restart—if a record was seen before the last shutdown, don't re-fire its event on the next poll.

### Async-Only
All I/O is async. Use `homeassistant.helpers.aiohttp_client.async_get_clientsession()` to get a shared aiohttp session. **Do not vendor** the reference Python libraries (`httpx`, `requests`) that use blocking I/O—they are incompatible with the HA async model.

## Critical Gotchas

### Behaviour Point Polarity
Behaviour points carry signed values (roughly −4 to +4). **Do not hardcode labels** like "Credit" or "Demerit"—instead derive the polarity from the sign and use the school's own label vocabulary from the API response. This respects school-specific terminology.

### Positive-Only Schools
Some schools hide negative points from parents (only credits visible). The demerit sensor must **degrade gracefully to `unknown`** if no negative points are returned, rather than assuming zero or emitting an error.

### Rate Limiting & Resilience
Back off on HTTP 429 (rate limit) and 5xx errors. Use a single shared `aiohttp.ClientSession` to improve connection pooling and respect rate limits across all children.

### Config Entry & Credentials
- Config-flow only; no YAML configuration
- Parent credentials (email, password, client credentials) stored in the HA config entry and encrypted at rest by HA
- **Never log credentials.** Redact them in `diagnostics.py` before returning debug data.

### IoT Class
Set `"iot_class": "cloud_polling"` in `manifest.json`. The integration requires outbound HTTPS to Satchel's servers.

## Testing

When implementation code exists:
- **Test framework:** `pytest` with `pytest-homeassistant-custom-component`
- **Fixtures:** Tests run against recorded JSON fixtures in `tests/fixtures/`, not live API
- **No live API in CI:** All responses are pre-recorded from Phase 0 capture
- **Unit test the models and client** (client against fixtures), then integration-test the coordinator and entities via Home Assistant's test harness

## Key Files to Study When Implementing

1. **Spec document:** `satchel_one_ha_integration_spec.md` — comprehensive reference
2. **HA custom component examples:** Home Assistant's integration architecture docs
3. **DataUpdateCoordinator pattern:** HA's `homeassistant.helpers.update_coordinator`
4. **Entity & Device patterns:** HA's `homeassistant.components.sensor`, `binary_sensor`

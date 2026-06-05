# Satchel One for Home Assistant

[![CI](https://github.com/wheezer256/satchel-one/actions/workflows/ci.yml/badge.svg)](https://github.com/wheezer256/satchel-one/actions/workflows/ci.yml)
[![hassfest](https://github.com/wheezer256/satchel-one/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/wheezer256/satchel-one/actions/workflows/hassfest.yaml)
[![HACS validate](https://github.com/wheezer256/satchel-one/actions/workflows/validate.yaml/badge.svg)](https://github.com/wheezer256/satchel-one/actions/workflows/validate.yaml)
[![Release](https://img.shields.io/github/v/release/wheezer256/satchel-one?sort=semver)](https://github.com/wheezer256/satchel-one/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration (HACS-distributable) that surfaces your child's school data from [Satchel One](https://www.satchelone.com/) into HA entities and events.

> **Unofficial.** This is a community project and is **not** affiliated with, endorsed by, or supported by Satchel One / Teach Computing. See the [Disclaimer](#disclaimer) and [Privacy & data protection](#privacy--data-protection) below.

## What it does

Per child linked to your parent account:

### Sensors
| Entity | State | Notes |
|---|---|---|
| `sensor.<child>_homework_due` | Count of outstanding tasks | Attributes: full task list with due dates |
| `sensor.<child>_next_homework` | ISO timestamp of next due task | |
| `sensor.<child>_credits` | Running total of positive behaviour points | Attributes: recent events |
| `sensor.<child>_demerits` | Running total of negative behaviour points | `unknown` for positive-only schools |
| `sensor.<child>_conduct_net` | Credits minus demerits | Attributes: week/month breakdown |
| `sensor.<child>_detentions` | Count of upcoming detentions | Attributes: list with dates and locations |

### Binary sensors
| Entity | State | Notes |
|---|---|---|
| `binary_sensor.<child>_overdue_homework` | `on` when any incomplete task is past due | |
| `binary_sensor.<child>_detention_today` | `on` when a detention is scheduled today | |

All entities carry a `linked_person` attribute (the mapped `person.*` entity_id) for use in automations.

### Events
| Event | Fired when | Key payload fields |
|---|---|---|
| `satchel_one_new_homework` | New task assigned | `task_id`, `title`, `subject`, `teacher`, `due_date`, `person` |
| `satchel_one_credit` | Positive behaviour event | `points`, `severity`, `reason`, `teacher`, `happened_on`, `person` |
| `satchel_one_demerit` | Negative behaviour event | `points`, `severity`, `reason`, `teacher`, `happened_on`, `person` |

`severity` = `abs(points)` — use this in automations to branch on seriousness without sign maths.

---

## Installation

### HACS (recommended)
1. In HACS → **Integrations** → ⋮ → **Custom repositories**, add
   `https://github.com/wheezer256/satchel-one` with category **Integration**.
2. Install **Satchel One**.
3. Restart Home Assistant.

### Manual
Copy `custom_components/satchel_one/` into your HA `config/custom_components/` directory and restart.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration → Satchel One**.
2. **Find your school** — type your school's name and pick it from the matches.
3. **Sign in** — enter your Satchel One **parent account** email and password.
4. The integration discovers your linked children automatically.
5. Optionally **link each child** to an existing `person.*` entity in HA (the
   dropdown lists each child by name).

---

## Configuration

After setup, click **Configure** on the integration card to adjust:

- **Homework poll interval** (default 30 min, minimum 5 min)
- **Behaviour poll interval** (default 15 min, minimum 5 min)
- **Child → person mapping** (update which person entity each child maps to)

---

## Example automations

### Notify when a demerit is issued

```yaml
alias: Notify on demerit
trigger:
  - platform: event
    event_type: satchel_one_demerit
condition:
  - condition: template
    value_template: "{{ trigger.event.data.person == 'person.alex' }}"
action:
  - service: notify.mobile_app_my_phone
    data:
      title: "Demerit — {{ trigger.event.data.reason }}"
      message: >
        {{ trigger.event.data.points }} pts
        (severity {{ trigger.event.data.severity }})
        on {{ trigger.event.data.happened_on }}
```

### Notify when new homework is assigned

```yaml
alias: Notify on new homework
trigger:
  - platform: event
    event_type: satchel_one_new_homework
action:
  - service: notify.mobile_app_my_phone
    data:
      title: "New homework — {{ trigger.event.data.subject }}"
      message: >
        {{ trigger.event.data.title }}
        due {{ trigger.event.data.due_date[:10] }}
```

### Screen time enforcement

The `satchel_one_demerit` event includes a `severity` field (`abs(points)`) so you can branch on seriousness. If you use Google FamilyLink for screen time, HA does not have a direct FamilyLink integration — but you can use the event to trigger a notification to review screen time manually, or combine it with any other enforcement mechanism you have in HA.

Example: send a persistent notification when severity ≥ 3:

```yaml
alias: High severity demerit alert
trigger:
  - platform: event
    event_type: satchel_one_demerit
condition:
  - condition: template
    value_template: "{{ trigger.event.data.severity >= 3 }}"
action:
  - service: persistent_notification.create
    data:
      title: "Serious demerit"
      message: >
        {{ trigger.event.data.reason }}
        ({{ trigger.event.data.points }} pts)
```

---

## Not yet implemented

- **Attendance** — the attendance API endpoint has not been captured from live traffic for this school. When captured, a Phase 0-style fixture + `AttendanceSensor` can be added. See `const.py` for the TODO marker.

---

## Notes

- This integration uses the **unofficial, reverse-engineered** Satchel One REST API. It may break without notice if Satchel One changes their API.
- Default poll intervals: homework 30 min, behaviour/detentions 15 min. Both configurable with a 5-minute floor.
- All credentials are stored encrypted at rest by Home Assistant.
- Diagnostics (Settings → Devices & Services → Satchel One → Enable debug logging / Download diagnostics) return a redacted snapshot with no tokens or student PII.

---

## Disclaimer

This is an independent, community-built integration. It is **not** affiliated
with, endorsed by, supported by, or connected to Satchel One, Teach Computing,
or any school.

- It talks to an **unofficial, reverse-engineered** API. There is no guarantee of
  availability or correctness, and it may stop working at any time if Satchel One
  changes their service.
- Provided **as is, without warranty of any kind** (see [LICENSE](LICENSE)). You
  use it at your own risk.
- Use it only with **your own parent account** to access **your own children's**
  data. You are responsible for complying with Satchel One's terms of service.

## Privacy & data protection

This integration is designed to keep your family's data under your control:

- It communicates **only** between your own Home Assistant instance and Satchel
  One's API — there are **no third-party servers** involved.
- Your credentials are stored in Home Assistant's config entry, **encrypted at
  rest**, and are never logged. Diagnostics output is redacted.
- It reads **only** the school data your own parent account can already see, and
  stores it on the Home Assistant instance **you** run.
- You remain the data controller for the information held in your Home Assistant.
  If you stop using the integration, delete the config entry to remove the stored
  credentials and data.

---

## Roadmap

- [x] Phase 0: API capture + sanitised fixtures
- [x] Phase 1: Async client + models
- [x] Phase 2: Config flow (auto-discovers children) + homework sensors
- [x] Phase 3: Behaviour sensors + event firing + person linking
- [x] Phase 4: Detentions sensor + binary sensors + diagnostics + reauth
- [x] Phase 5: Options flow (poll intervals + person re-mapping)
- [x] **1.0:** verified end-to-end against the live API; public release
- [ ] Silent token refresh (currently reauth re-prompts for the password)
- [ ] Attendance (needs live endpoint capture first)

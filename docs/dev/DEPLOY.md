# Deploying to Home Assistant

This is a config-flow integration — no YAML config needed.

> Replace the placeholders below with your own values:
> - `<REPO>` — where you cloned this repository
> - `<HA_CONFIG>` — your Home Assistant config directory (the one containing `configuration.yaml`)
> - `<HA_CONTAINER>` — your Home Assistant container name (if running in Docker)
> - `<HA_URL>` — your HA base URL (e.g. `http://localhost:8123`)
> - `<TOKEN>` — a long-lived access token (Profile → Security → Long-lived access tokens)

## Manual install

```bash
# 1. Copy the component into HA's custom_components directory
cp -r <REPO>/custom_components/satchel_one \
      <HA_CONFIG>/custom_components/satchel_one

# 2. Restart Home Assistant
#    (Docker: `docker restart <HA_CONTAINER>`, or use Developer Tools → Restart)

# 3. After restart, check the log for errors
#    (Docker: `docker logs <HA_CONTAINER> 2>&1 | grep -i satchel | tail -20`)
```

## Add the integration in HA UI

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Satchel One**
3. **Step 1 — Credentials:** enter parent account email + password
4. **Step 2 — Link children:** the integration auto-discovers children; optionally map each child to a `person.*` entity

## Verify entities are live

```bash
curl -s <HA_URL>/api/states \
  -H "Authorization: Bearer <TOKEN>" \
  | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    if 'satchel' in s['entity_id']:
        print(s['entity_id'], '=', s['state'])
"
```

Expected entities (per child):
- `sensor.<child>_homework_due`
- `sensor.<child>_next_homework`
- `sensor.<child>_credits`
- `sensor.<child>_demerits`
- `sensor.<child>_conduct_net`
- `sensor.<child>_detentions`
- `binary_sensor.<child>_overdue_homework`
- `binary_sensor.<child>_detention_today`

## Configure poll intervals

After setup: **Settings → Devices & Services → Satchel One → Configure**
- Homework poll interval (default 30 min, min 5 min)
- Behaviour poll interval (default 15 min, min 5 min)
- Update child → person mappings

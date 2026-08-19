# Enphase Battery RBD — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Controls the **Restrict Battery Discharge (RBD)** master switch on Enphase IQ Batteries directly from Home Assistant — the same toggle you see in the Enphase app under Menu → Battery → Restrict battery discharge.

## What it does

Exposes three entities per Enphase site:

| Entity | Type | Description |
|---|---|---|
| `switch.restrict_battery_discharge` | Switch | ON = battery protected (will not discharge), OFF = discharges normally |
| `button.recreate_rbd_schedule` | Button | Recreates the default 24h schedule if it was accidentally deleted |
| `sensor.enlighten_session_status` | Sensor | OK / ERROR — Enlighten cloud session health |

---

## Installation

### HACS (recommended)
1. Add `https://github.com/BartRoels/ha-enphase-battery` as a **custom repository** in HACS (type: Integration)
2. Install **Enphase Battery RBD**
3. Restart Home Assistant

### Manual
Copy the `custom_components/enphase_battery_rbd` folder to your `/config/custom_components/` directory and restart.

---

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **"Enphase Battery RBD"**. You will be asked for:

| Field | Description |
|---|---|
| **Enlighten Email** | Your Enphase Enlighten account email |
| **Enlighten Password** | Your Enphase Enlighten account password |
| **Create default 24h RBD schedule automatically** | Recommended — ON by default |

### About the schedule toggle

The RBD master switch only has an effect **when at least one RBD time schedule exists**. With the toggle enabled (default), the integration automatically creates a 00:00–23:59 all-days schedule during setup — so the switch works immediately without needing to open the Enphase app.

If you already have a schedule set up in the Enphase app, you can leave the toggle on (it will replace your existing schedule with an identical all-day one) or turn it off to keep your existing schedule untouched.

If the schedule is ever accidentally deleted from the Enphase app, press the **Recreate RBD Schedule** button entity to restore it instantly.

---

## How it works

The integration replicates the exact authentication flow used by the Enphase battery-profile-ui web app:

1. Logs in to Enlighten with your email and password
2. Obtains a JWT and full session cookie jar (including the session cookie)
3. Refreshes a BP-XSRF-Token via the schedule `isValid` endpoint
4. Calls `PUT /batterySettings/{battery_id}?userId={user_id}&source=enho` with `{"rbdControl": {"enabled": true|false}}`

> **Key technical insight:** the `batterySettings` endpoint requires a **full Enlighten session** (cookie jar + XSRF token), not just a JWT. A JWT alone returns 403 for homeowner accounts. This integration replicates the complete browser session the Enphase app uses — which is why it works where other approaches fail.

The session is refreshed every 15 minutes automatically. If your Enlighten password changes, HA will show a re-authentication notification so you can update your credentials without reinstalling.

---

## Example automation

Protect the battery while an EV is charging:

```yaml
automation:
  - alias: "Protect battery while EV charges"
    trigger:
      - trigger: state
        entity_id: input_boolean.ev_charging
        to: "on"
    action:
      - action: switch.turn_on
        target:
          entity_id: switch.restrict_battery_discharge

  - alias: "Release battery after EV charging"
    trigger:
      - trigger: state
        entity_id: input_boolean.ev_charging
        to: "off"
    action:
      - action: switch.turn_off
        target:
          entity_id: switch.restrict_battery_discharge
```

---

## Why not use existing integrations?

| Integration | Approach | Why it fails |
|---|---|---|
| `chinedu40/hacs_enphase_envoy_cloud` | Schedule API (POST) | Schedules land as `pending` — not enforced by hardware without the app's Apply step. Useful for managing schedules alongside this integration. |
| `barneyonline/ha-enphase-energy` | `set_mode` via batterySettings | Missing full cookie jar → 403/500 for most homeowner accounts |
| Local Envoy API (battery mode switch) | `backup` mode | Unreliable — writes don't consistently reach the hardware |

This integration uses the proven `batterySettings` PUT with full session authentication — the only approach confirmed to work end-to-end without the app's Apply button.

---

## Credits

Authentication flow reverse-engineered from the Enphase battery-profile-ui web app, with foundational research from [chinedu40/hacs_enphase_envoy_cloud](https://github.com/chinedu40/hacs_enphase_envoy_cloud) and [chinedu40/enphase_HA_REST_API](https://github.com/chinedu40/enphase_HA_REST_API).

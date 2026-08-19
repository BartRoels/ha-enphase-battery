# Enphase Battery RBD — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Controls the **Restrict Battery Discharge (RBD)** master switch on Enphase IQ Batteries directly from Home Assistant — the same toggle you see in the Enphase app under Menu → Battery → Restrict battery discharge.

## What it does

Exposes a single switch entity per Enphase site:

| Switch state | Meaning |
|---|---|
| **ON** | RBD enabled — battery will **not** discharge (protected) |
| **OFF** | RBD disabled — battery discharges normally per system profile |

### Important: schedule required

The RBD master switch (what this integration controls) only has an effect **when at least one RBD time schedule exists**. Without a schedule, toggling the switch does nothing at the hardware level.

You have two ways to create the schedule:

**Option A — Enphase app (recommended for most users)**
1. Open the Enphase app → Menu → Battery → Restrict battery discharge
2. Tap **Add schedule**
3. Set the window to **12:00 am – 11:59 pm**, select **Everyday**
4. Tap **Proceed** then **Apply**

A single 24-hour/every-day schedule is enough. Once it exists, this integration's switch controls whether it is active or not — you never need to touch the app again.

**Option B — `chinedu40/hacs_enphase_envoy_cloud`**
The [Enphase Envoy Cloud Control](https://github.com/chinedu40/hacs_enphase_envoy_cloud) integration exposes schedule editor entities in HA that can create and delete RBD schedules programmatically. Install it alongside this integration to manage the schedule from HA entirely.

> **Tip:** create the schedule once (via the app or the other integration) and leave it in place permanently. This integration then gives you a clean on/off switch for the restriction without touching the schedule itself.

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

## Installation

### HACS (recommended)
1. Add `https://github.com/BartRoels/ha-enphase-battery` as a **custom repository** in HACS (type: Integration)
2. Install **Enphase Battery RBD**
3. Restart Home Assistant

### Manual
Copy the `custom_components/enphase_battery_rbd` folder to your `/config/custom_components/` directory and restart.

---

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **"Enphase Battery RBD"**. Enter your Enlighten email and password. The integration auto-discovers your site ID and user ID.

---

## Entities

| Entity | Type | Description |
|---|---|---|
| `switch.restrict_battery_discharge` | Switch | ON = protected, OFF = discharging allowed |
| `sensor.enlighten_session_status` | Sensor | OK / ERROR — cloud session health |

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
| `chinedu40/hacs_enphase_envoy_cloud` | Schedule API (POST) | Schedules land as `pending` — not enforced by hardware without the app's Apply step. Use it to manage schedules, not to toggle RBD. |
| `barneyonline/ha-enphase-energy` | `set_mode` via batterySettings | Missing full cookie jar → 403/500 for most homeowner accounts |
| Local Envoy API (battery mode switch) | `backup` mode | Unreliable — writes don't consistently reach the hardware |

This integration uses the proven `batterySettings` PUT with full session authentication — the only approach confirmed to work end-to-end without the app's Apply button.

---

## Credits

Authentication flow reverse-engineered from the Enphase battery-profile-ui web app, with foundational research from [chinedu40/hacs_enphase_envoy_cloud](https://github.com/chinedu40/hacs_enphase_envoy_cloud) and [chinedu40/enphase_HA_REST_API](https://github.com/chinedu40/enphase_HA_REST_API).

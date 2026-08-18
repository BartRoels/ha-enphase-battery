# Enphase Battery RBD — Home Assistant Integration

Controls the **Restrict Battery Discharge (RBD)** feature on Enphase IQ Batteries directly from Home Assistant, without needing to open the Enphase app.

## What it does

Exposes a single switch entity per Enphase site:

| Switch state | Meaning |
|---|---|
| **ON** | RBD enabled — battery will **not** discharge (protected) |
| **OFF** | RBD disabled — battery discharges normally per system profile |

## How it works

The integration replicates the exact authentication flow used by the Enphase battery-profile-ui web app:

1. Logs in to Enlighten with your email and password
2. Obtains a JWT and full session cookie jar
3. Refreshes a BP-XSRF-Token via the schedule `isValid` endpoint
4. Calls `PUT /batterySettings/{battery_id}?userId={user_id}&source=enho` with `{"rbdControl": {"enabled": true|false}}`

> **Key insight:** the `batterySettings` endpoint requires a full Enlighten session (cookie jar + XSRF token), not just a JWT. A JWT alone returns 403. This is why all previous integration attempts failed.

## Installation

### HACS
Add this repository as a custom repository in HACS (type: Integration), install "Enphase Battery RBD", restart HA.

### Manual
Copy `custom_components/enphase_battery_rbd` to your HA config directory and restart.

## Configuration

Settings → Devices & Services → Add Integration → search "Enphase Battery RBD". Enter your Enlighten email and password. Site ID and user ID are auto-discovered.

## Entities

| Entity | Type | Description |
|---|---|---|
| `switch.restrict_battery_discharge` | Switch | ON = protected, OFF = discharging allowed |
| `sensor.enlighten_session_status` | Sensor | OK / ERROR |

## Why not use existing integrations?

| Integration | Approach | Why it fails |
|---|---|---|
| `chinedu40/hacs_enphase_envoy_cloud` | Schedule API | Schedules stay `pending` — not enforced without app Apply |
| `barneyonline/ha-enphase-energy` | `set_mode` via batterySettings | Missing full cookie jar → 403/500 |
| Local Envoy API | Battery mode switch | Unreliable — writes don't always reach hardware |

## Credits

Authentication flow reverse-engineered from the Enphase battery-profile-ui web app, with foundational work from chinedu40/hacs_enphase_envoy_cloud and chinedu40/enphase_HA_REST_API.

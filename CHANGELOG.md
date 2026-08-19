# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2026-08-18

### Added
- `switch.restrict_battery_discharge` — ON = battery protected (RBD enabled), OFF = battery discharges normally
- `sensor.enlighten_session_status` — OK/ERROR Enlighten cloud session health indicator
- Auto-discovery of battery site ID and user ID from Enlighten session
- Re-authentication flow — HA notifies you if your Enlighten password changes instead of silently failing
- Session refresh every 15 minutes via DataUpdateCoordinator
- HACS icon — battery with padlock

### Technical
- Full Enlighten session authentication (cookie jar + XSRF token) — the only approach confirmed to work for the `batterySettings` PUT endpoint without installer-level API access
- `batterySettings PUT /rbdControl` used directly, bypassing the unreliable schedule pending/active flow

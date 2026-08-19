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

## [0.1.1] - 2026-08-19

### Added
- HACS icon — battery with padlock
- Automated GitHub Actions release workflow
- HACS and hassfest validation actions (required for HACS default store)
- CHANGELOG.md

### Changed
- README: clarified that a schedule must exist first (via Enphase app or chinedu40 integration) before the switch has any effect
- README: added comparison table and schedule setup instructions

## [0.2.0] - 2026-08-19

### Added
- **Config flow toggle**: "Create default 24h RBD schedule automatically" (enabled by default). When checked during setup, the integration creates a 00:00–23:59 all-days RBD schedule so the switch works immediately — no need to open the Enphase app first.
- **Button entity**: `button.recreate_rbd_schedule` — recreates the default schedule with one tap, useful if it was accidentally deleted from the Enphase app.

### Changed
- Schedule creation failure during setup is non-fatal — the integration still sets up successfully and the button can be used to retry.
- `create_default_schedule()` now deletes any conflicting existing schedules before creating a fresh one (avoids 409 conflict errors).
- Timezone is read from HA config and passed to Enphase when creating schedules.

## [0.2.1] - 2026-08-19

### Fixed
- Remove invalid `quality_scale: "custom"` from manifest.json (caused hassfest validation failure)
- Remove orphaned entity strings from strings.json (entity names are set via `_attr_name` directly)
- Release workflow: set `make_latest: true` to handle pre-existing release tags gracefully

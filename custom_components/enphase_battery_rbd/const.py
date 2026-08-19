"""Constants for Enphase Battery RBD integration."""

DOMAIN = "enphase_battery_rbd"

# Config entry keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_BATTERY_ID = "battery_id"
CONF_USER_ID = "user_id"
CONF_CREATE_SCHEDULE = "create_schedule"

# Update interval
UPDATE_INTERVAL_SECONDS = 900  # 15 minutes

# Enlighten URLs
ENLIGHTEN_BASE = "https://enlighten.enphaseenergy.com"
BATTERY_CONFIG_BASE = f"{ENLIGHTEN_BASE}/service/batteryConfig/api/v1"
BATTERY_PROFILE_ORIGIN = "https://battery-profile-ui.enphaseenergy.com"

# Device info
MANUFACTURER = "Enphase Energy"
MODEL = "IQ Battery (Cloud RBD Control)"

# Entity names
SWITCH_RBD_NAME = "Restrict Battery Discharge"
SENSOR_SESSION_NAME = "Enlighten Session Status"
BUTTON_RECREATE_NAME = "Recreate RBD Schedule"

# Default schedule settings
DEFAULT_SCHEDULE_START = "00:00"
DEFAULT_SCHEDULE_END = "23:59"
DEFAULT_SCHEDULE_DAYS = [1, 2, 3, 4, 5, 6, 7]  # Mon–Sun

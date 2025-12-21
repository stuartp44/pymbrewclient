# API Response Examples

This document contains example payloads returned by the Minibrew API.

## Brewery Overview Response

The `get_brewery_overview()` method returns the current status of all devices in your brewery, including brewing devices, kegs, and their current states.

### Example Response

```json
{
    "brew_clean_idle": [
        {
            "uuid": "XXXXXXXX-XXXXXXXX",
            "serial_number": "XXXXXXXX-XXXXXXXX",
            "device_type": 0,
            "user_action": 0,
            "process_type": 0,
            "title": "My MiniBrew",
            "sub_title": "Connected",
            "session_id": null,
            "image": "https://minibrew.s3.amazonaws.com/static/devices/base.png",
            "status_time": null,
            "stage": "Idle",
            "beer_name": null,
            "recipe_version": null,
            "beer_style": null,
            "gravity": "1.00",
            "target_temp": null,
            "current_temp": null,
            "online": true,
            "updating": false,
            "needs_acid_cleaning": false,
            "is_starting": null,
            "software_version": "3.2.3, idf-v4.2-50-g11005797d"
        }
    ],
    "fermenting": [
        {
            "uuid": "YYYYYYYY-YYYYYYYY",
            "serial_number": "YYYYYYYY-YYYYYYYY",
            "device_type": 1,
            "user_action": 0,
            "process_type": 4,
            "title": "Keg YYYYYYYY",
            "sub_title": "Connected",
            "session_id": 12345,
            "image": "https://minibrew.s3.amazonaws.com/static/devices/keg.png",
            "status_time": 824550,
            "stage": "Primary",
            "beer_name": "Example Beer",
            "recipe_version": "1",
            "beer_style": "Example Style",
            "gravity": "1.00",
            "target_temp": 14.91,
            "current_temp": 15.1,
            "online": true,
            "updating": false,
            "needs_acid_cleaning": false,
            "is_starting": false,
            "software_version": "3.2.3, idf-v4.2-50-g11005797d"
        }
    ],
    "serving": [],
    "brew_acid_clean_idle": []
}
```

### Response Structure

The response is organized into different categories based on device state:

#### Categories

- **`brew_clean_idle`**: Brewing devices that are idle, clean, and ready to use
- **`fermenting`**: Kegs currently fermenting beer
- **`serving`**: Kegs currently serving beer
- **`brew_acid_clean_idle`**: Brewing devices that need acid cleaning

#### Device Fields

| Field | Type | Description |
|-------|------|-------------|
| `uuid` | string | Unique device identifier |
| `serial_number` | string | Device serial number |
| `device_type` | integer | Type of device (0=brewer, 1=keg) |
| `user_action` | integer | Current user action state |
| `process_type` | integer | Current process type |
| `title` | string | Custom device name |
| `sub_title` | string | Connection status |
| `session_id` | integer/null | Current brewing session ID (if active) |
| `image` | string | URL to device image |
| `status_time` | integer/null | Time in current state (seconds) |
| `stage` | string | Current stage (e.g., "Idle", "Primary", "Secondary") |
| `beer_name` | string/null | Name of beer being brewed/fermented |
| `recipe_version` | string/null | Recipe version number |
| `beer_style` | string/null | Style of beer |
| `gravity` | string | Current specific gravity reading |
| `target_temp` | float/null | Target temperature in Celsius |
| `current_temp` | float/null | Current temperature in Celsius |
| `online` | boolean | Device online status |
| `updating` | boolean | Device firmware update in progress |
| `needs_acid_cleaning` | boolean | Device requires acid cleaning |
| `is_starting` | boolean/null | Device is starting up |
| `software_version` | string | Device firmware version |

### Device States

#### Idle Brewer
- `stage`: "Idle"
- `session_id`: null
- `beer_name`: null
- All temperature and gravity fields are null or default values

#### Fermenting Keg
- `stage`: "Primary" or "Secondary"
- `session_id`: Active session ID
- `beer_name`: Name of the beer
- `target_temp` and `current_temp`: Active fermentation temperatures
- `status_time`: Time elapsed in current stage (seconds)

#### Serving Keg
- `stage`: "Serving"
- Contains beer information
- Temperature maintained at serving temperature

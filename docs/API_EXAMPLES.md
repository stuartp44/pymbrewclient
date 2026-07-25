# API Response Examples

This document contains example payloads returned by the Minibrew API.

## Devices Response

The `get_devices()` method returns the authenticated device list from `/v1/devices/`.

### Example Response

```json
[
    {
        "uuid": "ZZZZZZZZ-ZZZZZZZZ",
        "serial_number": "ZZZZZZZZ-ZZZZZZZZ",
        "current_state": 2,
        "process_type": 2,
        "process_state": 101,
        "user_action": 2,
        "active_session": 80675,
        "connection_status": 1,
        "last_time_online": "2026-07-18T09:56:31.100000Z",
        "software_version": "3.2.3",
        "custom_name": "Fermenter 1",
        "device_type": 1,
        "image": "https://minibrew.s3.amazonaws.com/static/devices/keg.png",
        "last_process_state_change": "2026-07-18T09:45:16Z",
        "process_estimate_remaining": "2026-07-18T09:57:31.542739Z",
        "text": "Needs your attention",
        "updating": false
    }
]
```

### Process Estimate Notes

- `process_estimate_remaining` is an absolute UTC timestamp supplied by MiniBrew's REST API.
- The library parses `last_time_online`, `last_process_state_change`, and `process_estimate_remaining` into timezone-aware Python `datetime` objects.
- `process_estimate_remaining_seconds` is calculated locally from the REST timestamp and can be `0` even when the original timestamp is still preserved.
- This value can be stale or already in the past. It is not MiniBrew's live MQTT countdown.

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
            "beer_srm": null,
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
            "beer_srm": "12",
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
| `beer_srm` | string/null | Beer color value (SRM - Standard Reference Method) |
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

---

## MQTT-over-WebSocket

`pymbrewclient` supports real-time device telemetry over MQTT-over-WebSocket using
`create_mqtt_client()`.  The underlying broker is `broker.minibrew.io:15675/ws` (TLS).

> **Security warning:** The MiniBrew REST API token is used as the MQTT
> password.  Do **not** log the `MqttClient` object, its `repr()`, or any
> callback data in contexts where credentials could be exposed.

### Connection example

```python
from pymbrewclient import BreweryClient

client = BreweryClient(username="you@example.com", *****)

with client.create_mqtt_client() as mqtt:
    mqtt.on_connected(lambda: print("Connected"))
    mqtt.on_disconnected(lambda: print("Disconnected"))
    mqtt.on_reconnecting(lambda: print("Reconnecting..."))
    mqtt.on_error(lambda err: print(f"Error: {err}"))

    mqtt.subscribe_device_logs("7391Q4827-5NZC8R2M")

    import time
    time.sleep(30)
```

### Raw-message example

```python
from pymbrewclient.mqtt.models import MqttMessage

with client.create_mqtt_client() as mqtt:
    def handle(msg: MqttMessage) -> None:
        print(msg.topic, msg.received_at, msg.payload.hex())

    mqtt.on_message(handle)
    mqtt.subscribe_device_logs("7391Q4827-5NZC8R2M")
    import time; time.sleep(30)
```

### Decoded telemetry example

```python
from pymbrewclient.mqtt.models import DeviceLogMessage

with client.create_mqtt_client() as mqtt:
    def handle_log(msg: DeviceLogMessage) -> None:
        if msg.decode_error:
            print(f"Decode error: {msg.decode_error}")
            return
        print(f"Session {msg.session_id}")
        print(f"Process state: {msg.process_state}")
        print(f"Current temp: {msg.current_temperature}°C")
        print(f"Target temp:  {msg.target_temperature}°C")
        print(f"Wi-Fi RSSI:  {msg.wifi_rssi_dbm} dBm")
        if msg.next_action_at:
            print(f"Next action: {msg.next_action_at.isoformat()}")
        for measurement_id, value in msg.measurements.items():
            print(f"Measurement {measurement_id}: {value}")

    mqtt.on_device_log(handle_log)
    mqtt.subscribe_device_logs("7391Q4827-5NZC8R2M")
    import time; time.sleep(30)
```

### Limitations: protobuf schema

MiniBrew's official protobuf schema (`minibrew/minibrew-protobuf`) is a private
repository that is not publicly accessible. The fields exposed directly on
`DeviceLogMessage` were reconstructed from captured device traffic and compared
with the MiniBrew REST API response structure.

Unknown nested state values are exposed through `DeviceLogMessage.state_fields`.
Confirmed measurement ID 24 is also exposed as `DeviceLogMessage.wifi_rssi_dbm`;
all readings, including measurements whose semantics remain unconfirmed, stay
available by numeric ID in `DeviceLogMessage.measurements`. The raw `payload`
bytes are always preserved in `MqttMessage.payload` and
`DeviceLogMessage.payload`. To inspect a live message:

```bash
protoc --decode_raw < captured_payload.bin
```

Live MQTT messages contain an envelope around the telemetry message.
`DeviceLogMessage.raw_fields` exposes that envelope, while
`DeviceLogMessage.telemetry_fields` exposes the nested telemetry fields.
Telemetry field 26 is the countdown in seconds to the next required action;
`DeviceLogMessage.next_action_at` adds it to the device timestamp and returns a
timezone-aware UTC datetime. Unconfirmed fields, including telemetry fields 8
and 30, remain available without speculative semantic names.

The CLI prints curated decoded telemetry by default, excluding the binary
payload, numeric measurement map, and protobuf field maps. Confirmed named
measurements such as `wifi_rssi_dbm` remain visible:

```bash
pymbrewclient watch-device-logs \
  --username you@example.com \
  --password 'your-password' \
  --serial 7391Q4827-5NZC8R2M
```

Add `--debug` to include the complete numeric `measurements` map, raw payload,
`raw_fields`, `telemetry_fields`, and `state_fields`:

```bash
pymbrewclient watch-device-logs \
  --username you@example.com \
  --password 'your-password' \
  --serial 7391Q4827-5NZC8R2M \
  --debug
```

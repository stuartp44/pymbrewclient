# pymbrewclient

`pymbrewclient` is a Python library and CLI tool for interacting with MiniBrew's API. It provides both programmatic access and a command-line interface for fetching brewery, device, and session information.

## Disclaimer

This project is an independent, community-driven tool and is **not affiliated with, endorsed by, or supported by Minibrew**. It is developed and maintained by independent contributors.

## Requirements

This library will **only work** if you have access to Minibrew's Pro Portal subscription.

---

## Features

- Fetch brewery overview data.
- Fetch authenticated device data from `/v1/devices/`.
- Retrieve session information.
- Retrieve MiniBrew's REST process estimate as an absolute UTC timestamp.
- Calculate remaining seconds and a human-readable duration locally.
- Easy-to-use CLI for quick access.
- Python library for programmatic integration.
- Uses standard Python logging and stays silent by default unless your application enables DEBUG for `pymbrewclient`.

## Installation

You can install `pymbrewclient` using `pip`:

### CLI

```bash
pip install pymbrewclient
```

```bash
pymbrewclient get-token --username <USERNAME> --password <PASSWORD>
```

```bash
pymbrewclient get-brewery-overview --username <USERNAME> --password <PASSWORD>
```

```bash
pymbrewclient get-session-info --username <USERNAME> --password <PASSWORD> --sessionid <SESSION_ID>
```

```bash
pymbrewclient get-minibrew-devices --username <USERNAME> --password <PASSWORD>
```

```bash
pymbrewclient process-estimate --username <USERNAME> --password <PASSWORD> --session-id 80675
```

```bash
pymbrewclient process-estimate --username <USERNAME> --password <PASSWORD> --device-uuid <UUID> --format json
```

### Library Usage

```python
from pymbrewclient.client import BreweryClient

client = BreweryClient(username, password)

brewery_overview = client.get_brewery_overview()
print(brewery_overview)
```

```python
from pymbrewclient.client import BreweryClient

client = BreweryClient(username, password)

session_id = 12345
session_info = client.get_session_info(session_id)
print(session_info)
```

```python
from pymbrewclient.client import BreweryClient

client = BreweryClient(username, password)

devices = client.get_devices()
device = devices[0]

print(device.process_estimate_remaining)
print(device.process_estimate_remaining_seconds)
print(device.process_estimate_remaining_formatted)
```

```python
from pymbrewclient.client import BreweryClient

client = BreweryClient(username, password)

estimate = client.get_process_estimate(device_uuid="your-device-uuid")
remaining_seconds = client.get_process_estimate_remaining_seconds(device_uuid="your-device-uuid")

print(estimate)
print(remaining_seconds)
```

```python
from pymbrewclient.client import BreweryClient

client = BreweryClient(username, password)

estimate = client.get_process_estimate(session_id=80675)
remaining_seconds = client.get_process_estimate_remaining_seconds(session_id=80675)

print(estimate)
print(remaining_seconds)
```

## Process Estimate Notes

`process_estimate_remaining` is an absolute UTC timestamp returned by MiniBrew's REST API.

- The library parses REST timestamps into timezone-aware Python `datetime` objects.
- `process_estimate_remaining_seconds` and `process_estimate_remaining_formatted` are calculated locally from the REST timestamp, so they are point-in-time snapshots and naturally become stale.
- MiniBrew can return an estimate that is already in the past when a device is paused, needs user attention, has stopped reporting, or when the backend estimate has not refreshed yet.
- This feature exposes the REST estimate only. It is not MiniBrew's live MQTT countdown.

## MQTT Telemetry Requests

Use `subscribe_device_logs()` to subscribe to a device and request frequent
telemetry without opening the MiniBrew portal:

```python
from pymbrewclient import BreweryClient

client = BreweryClient(username, password)
with client.create_mqtt_client() as mqtt:
    mqtt.on_device_log(lambda message: print(message.current_temperature))
    mqtt.on_error(lambda error: print(f"MQTT error: {error}"))
    mqtt.subscribe_device_logs("your-device-serial")
    input("Press Enter to disconnect\n")
```

The helper subscribes to `devices/logs/<serial>` and
`devices/logrequests/<serial>`, then publishes MiniBrew's protobuf start-log
request to `apps/logrequests/<serial>`. The requester is this client's plain
UUID; requests use QoS 0 and are not retained.

- A background watchdog re-requests logs after at least five seconds without
  incoming telemetry, checking once per second. Unchanged packets still count
  as activity; request responses do not.
- While packets continue arriving, no periodic application request is sent.
  The normal 60-second MQTT keepalive remains unchanged.
- Subscriptions and start-log requests are restored after broker reconnects.
- `unsubscribe_device_logs()` stops this client's log request and removes both
  device topics. `disconnect()` stops the watchdog and sends stop-log requests
  while connected, retaining subscriptions for a later reconnect.
- `on_message()` exposes raw log-request responses. Publish failures are logged
  and delivered to `on_error()`.
- Generic `subscribe()` remains subscription-only. Use it if you do not want
  the automatic frequent-log requests and recovery behaviour.

The protocol was verified against portal traffic: a start request was followed
by telemetry at about one packet per second, and the portal repeated the
request after five seconds without logs. This does not guarantee telemetry
from an offline device or establish that a request caused recovery.

## Development

Clone the repository:
```
git clone https://github.com/yourusername/pymbrewclient.git
cd pymbrewclient
```

Install dependencies:
```
pip install .[dev]
```

Run tests:
```
pytest
```

Lint the code:
```
make lint
```
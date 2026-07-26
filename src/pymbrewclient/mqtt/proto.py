# "Commons Clause" License Condition v1.0
#
# The Software is provided to you by the Licensor under the License, as defined below, subject to the following condition.
#
# Without limiting other conditions in the License, the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.
#
# For purposes of the foregoing, "Sell" means practicing any or all of the rights granted to you under the License to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/ support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software. Any license notice or attribution required by the License must also include this Commons Clause License Condition notice.
#
# Software: pymbrewclient
# License: MIT License
# Licensor: Stuart Pearson
#
#
# MIT License
#
# Copyright (c) 2024 Stuart Pearson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Disclaimer: This software is an independent project and is not affiliated with, endorsed by, or associated with MiniBrew. MiniBrew's trademarks, logos, API, and other intellectual property are owned by MiniBrew and are not included in this software. Users are responsible for complying with MiniBrew's terms of service when using this software.
"""
Pure-Python protobuf wire-format decoder for MiniBrew device-log messages.

Why pure Python?
    MiniBrew's official ``.proto`` source (``minibrew/minibrew-protobuf``) is
    private.  The field numbers here are RECONSTRUCTED from community
    documentation and the MiniBrew REST API; they are not guaranteed to match
    the real schema.  Using a pure wire-format decoder avoids a hard dependency
    on a specific ``google.protobuf`` version and makes the mapping explicit.

Schema caveat
    Field numbers are labelled "best-effort".  Until an official schema is
    published, decoded values should be treated as approximate.  Use
    ``DeviceLogMessage.raw_fields`` or ``MqttMessage.payload`` to inspect the
    raw wire data.

    To dump a live message: ``protoc --decode_raw < captured_payload.bin``

Observed telemetry structure
    =========  ==============================  ============================
    Field No.  Name                            Wire type
    =========  ==============================  ============================
    1          device_timestamp                varint (Unix epoch ms)
    2          state                           nested message
    3          measurements                    repeated nested ``{id,float}``
    11         session_id                      varint
    18         target_temperature              32-bit float
    19         current_temperature             32-bit float
    26         seconds_until_next_action       varint
    =========  ==============================  ============================

Measurement entries (outer field 3) are keyed by ``SensorType`` (see
``.enums``); e.g. ID 3 is ``TEMP_LIQUID`` and ID 24 is ``TEMP_CONTROL_POWER``
(signed Peltier power, negative = cooling).

The nested state message has observed fields 1 (current state), 2 (process
type), 3 (process state), and 8 (user action). Unknown outer, state, and
measurement fields remain available without speculative names.

Live broker messages wrap this telemetry message in an envelope with field 1
(sequence number), field 3 (nested telemetry), field 4 (session ID), and field
5 (Unix epoch milliseconds).
"""

import struct
from datetime import datetime, timedelta, timezone

from .enums import SensorType
from .models import DeviceLogMessage, MqttMessage

# ---------------------------------------------------------------------------
# Wire-type constants
# ---------------------------------------------------------------------------
_WIRE_VARINT = 0
_WIRE_64BIT = 1
_WIRE_LEN_DELIM = 2
_WIRE_32BIT = 5


# ---------------------------------------------------------------------------
# Low-level wire decoder
# ---------------------------------------------------------------------------


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Decode a protobuf base-128 varint starting at *pos*.

    Returns ``(value, new_position)``.  Raises ``ValueError`` for truncated or
    over-long varints.
    """
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7
        if shift >= 64:
            raise ValueError("Varint exceeds 64 bits — data may be corrupt")
    raise ValueError("Truncated varint — unexpected end of data")


def decode_raw_fields(data: bytes) -> dict[int, list[object]]:
    """Decode raw protobuf wire format into ``{field_number: [values]}``.

    All fields are decoded regardless of whether their numbers are known.
    Varint fields are returned as ``int``, 32-bit fields as ``bytes`` (4
    bytes, little-endian), 64-bit fields as ``bytes`` (8 bytes,
    little-endian), and length-delimited fields as ``bytes``.

    :param data: Raw protobuf payload bytes.
    :returns: A dict mapping each field number to the list of values seen for
              that field (repeated fields produce multiple entries).
    :raises ValueError: If the data contains a structurally invalid wire
                        encoding (truncated field, unknown wire type).
    """
    result: dict[int, list[object]] = {}
    pos = 0
    while pos < len(data):
        tag, pos = _decode_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7

        if wire_type == _WIRE_VARINT:
            value, pos = _decode_varint(data, pos)
            result.setdefault(field_number, []).append(value)

        elif wire_type == _WIRE_64BIT:
            if pos + 8 > len(data):
                raise ValueError(f"Truncated 64-bit field {field_number}")
            raw = data[pos : pos + 8]
            pos += 8
            result.setdefault(field_number, []).append(raw)

        elif wire_type == _WIRE_LEN_DELIM:
            length, pos = _decode_varint(data, pos)
            if pos + length > len(data):
                raise ValueError(f"Truncated length-delimited field {field_number}: expected {length} bytes")
            value = data[pos : pos + length]
            pos += length
            result.setdefault(field_number, []).append(value)

        elif wire_type == _WIRE_32BIT:
            if pos + 4 > len(data):
                raise ValueError(f"Truncated 32-bit field {field_number}")
            raw = data[pos : pos + 4]
            pos += 4
            result.setdefault(field_number, []).append(raw)

        else:
            raise ValueError(f"Unknown wire type {wire_type} for field {field_number}")

    return result


# ---------------------------------------------------------------------------
# High-level decoder
# ---------------------------------------------------------------------------


def _first_varint(raw: dict[int, list[object]], field_num: int) -> int | None:
    """Return the first varint value for *field_num*, or ``None``."""
    values = raw.get(field_num)
    if values and isinstance(values[0], int):
        return values[0]
    return None


def _first_float32(raw: dict[int, list[object]], field_num: int) -> float | None:
    """Return the first 32-bit float value for *field_num*, or ``None``."""
    values = raw.get(field_num)
    if values and isinstance(values[0], (bytes, bytearray)) and len(values[0]) == 4:
        return round(struct.unpack("<f", values[0])[0], 4)
    return None


def _first_bytes(raw: dict[int, list[object]], field_num: int) -> bytes | None:
    """Return the first length-delimited value for *field_num*, or ``None``."""
    values = raw.get(field_num)
    if values and isinstance(values[0], bytes):
        return values[0]
    return None


def _decode_measurements(raw: dict[int, list[object]]) -> dict[int, float]:
    """Decode repeated outer field 3 entries as measurement ID/value pairs."""
    measurements: dict[int, float] = {}
    for value in raw.get(3, []):
        if not isinstance(value, bytes):
            continue
        entry = decode_raw_fields(value)
        measurement_id = _first_varint(entry, 1)
        measurement_value = _first_float32(entry, 2)
        if measurement_id is not None and measurement_value is not None:
            measurements[measurement_id] = measurement_value
    return measurements


def _unwrap_telemetry(raw: dict[int, list[object]]) -> tuple[dict[int, list[object]], bool]:
    """Return telemetry fields and whether the payload used the live envelope."""
    nested = _first_bytes(raw, 3)
    if _first_varint(raw, 5) is None or nested is None:
        return raw, False
    return decode_raw_fields(nested), True


def decode_device_log(msg: MqttMessage) -> DeviceLogMessage:
    """Attempt to decode a ``devices/logs/`` MQTT message as a DeviceLog.

    On a decoding error the returned :class:`~pymbrewclient.mqtt.models.DeviceLogMessage`
    has :attr:`~pymbrewclient.mqtt.models.DeviceLogMessage.decode_error` set. Fields decoded
    before a nested-message error remain available. The raw
    :attr:`~pymbrewclient.mqtt.models.MqttMessage.payload` is always preserved.

    :param msg: The raw :class:`~pymbrewclient.mqtt.models.MqttMessage` to decode.
    :returns: A populated :class:`~pymbrewclient.mqtt.models.DeviceLogMessage`.
    """
    base = DeviceLogMessage(
        topic=msg.topic,
        payload=msg.payload,
        received_at=msg.received_at,
        device_uuid=msg.device_uuid,
    )

    try:
        raw = decode_raw_fields(msg.payload)
    except ValueError as exc:
        base.decode_error = f"Wire decode failed: {exc}"
        return base

    base.raw_fields = raw

    try:
        telemetry, is_wrapped = _unwrap_telemetry(raw)
    except ValueError as exc:
        base.decode_error = f"Telemetry decode failed: {exc}"
        return base

    base.telemetry_fields = telemetry

    # Confirmed from captured device traffic.
    if is_wrapped:
        base.sequence_number = _first_varint(raw, 1)
        base.session_id = _first_varint(raw, 4)
        timestamp_ms = _first_varint(raw, 5)
    else:
        base.session_id = _first_varint(telemetry, 11)
        timestamp_ms = _first_varint(telemetry, 1)

    if timestamp_ms is not None:
        try:
            base.device_timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        except (OSError, OverflowError, ValueError) as exc:
            base.decode_error = f"Invalid device timestamp: {exc}"

    state_payload = _first_bytes(telemetry, 2)
    if state_payload is not None:
        try:
            base.state_fields = decode_raw_fields(state_payload)
        except ValueError as exc:
            base.decode_error = f"Nested state decode failed: {exc}"
        else:
            base.current_state = _first_varint(base.state_fields, 1)
            base.process_type = _first_varint(base.state_fields, 2)
            base.process_state = _first_varint(base.state_fields, 3)
            base.user_action = _first_varint(base.state_fields, 8)

    try:
        base.measurements = _decode_measurements(telemetry)
    except ValueError as exc:
        base.decode_error = f"Measurement decode failed: {exc}"

    base.temp_control_power = base.measurements.get(SensorType.TEMP_CONTROL_POWER)
    base.process_phase = _first_varint(telemetry, 21)
    base.machine_type = _first_varint(telemetry, 22)
    base.current_temperature = _first_float32(telemetry, 19)
    base.target_temperature = _first_float32(telemetry, 18)
    base.seconds_until_next_action = _first_varint(telemetry, 26)
    if base.device_timestamp is not None and base.seconds_until_next_action is not None:
        base.next_action_at = base.device_timestamp + timedelta(seconds=base.seconds_until_next_action)

    return base

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
Typed message models for the MiniBrew MQTT client.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MqttMessage:
    """A raw MQTT message received from the broker."""

    topic: str
    """The full MQTT topic the message was published on."""

    payload: bytes
    """The raw message payload bytes, always preserved."""

    received_at: datetime
    """Timezone-aware UTC datetime when this message was received by the client."""

    device_uuid: str | None = None
    """
    Device UUID extracted from the topic when the topic follows the
    ``devices/{message_type}/{device_uuid}`` pattern; ``None`` otherwise.
    """


@dataclass
class DeviceLogMessage:
    """
    A decoded MiniBrew device-log telemetry message from the
    ``devices/logs/{SerialNumber}`` MQTT topic.

    **Schema caveat**: MiniBrew's official ``.proto`` source
    (``minibrew/minibrew-protobuf``) is a private repository and is not
    publicly available.  The field numbers used for decoding were
    reconstructed from the MiniBrew REST API response structure and the
    community-maintained ``minibrew/enduser-docker-server`` project.
    Fields may be mapped to wrong values until the official schema is
    confirmed.  The raw :attr:`payload` is always retained.

    All decoded fields default to ``None`` when absent from the message
    or when decoding fails.
    """

    topic: str
    """The full MQTT topic."""

    payload: bytes
    """Raw protobuf bytes — always present regardless of decode success."""

    received_at: datetime
    """Timezone-aware UTC datetime when this message was received."""

    device_uuid: str | None = None
    """Device serial / UUID extracted from the topic path."""

    # --- Decoded telemetry fields ----------------------------------------

    session_id: int | None = None
    """Active brewing session ID (protobuf field 1, best-effort)."""

    device_timestamp: datetime | None = None
    """
    Timezone-aware UTC datetime from the device's own clock
    (protobuf field 2, best-effort).  Derived from a Unix epoch integer.
    """

    process_state: int | None = None
    """
    Process state integer (protobuf field 3, best-effort).
    See ``PROCESS_STATE_LABELS`` in the MiniBrew community docs for a
    complete mapping (e.g. 80 → FERMENTATION_TEMP_CONTROL).
    """

    user_action: int | None = None
    """
    User-action state integer (protobuf field 4, best-effort).
    See ``USER_ACTION_LABELS`` in the MiniBrew community docs.
    """

    current_temperature: float | None = None
    """Current temperature in °C (protobuf field 5, best-effort)."""

    target_temperature: float | None = None
    """Target temperature in °C (protobuf field 6, best-effort)."""

    remaining_duration_seconds: int | None = None
    """Remaining process duration in seconds (protobuf field 7, best-effort)."""

    seconds_until_next_action: int | None = None
    """Seconds until the next scheduled action (protobuf field 8, best-effort)."""

    next_action_at: datetime | None = None
    """
    Calculated UTC datetime of the next scheduled action::

        next_action_at = device_timestamp + timedelta(seconds=seconds_until_next_action)

    ``None`` when either :attr:`device_timestamp` or
    :attr:`seconds_until_next_action` is absent.
    """

    decode_error: str | None = None
    """
    A brief description of any error encountered during protobuf decoding.
    When set, some or all decoded telemetry fields may be ``None``.
    The raw :attr:`payload` is unaffected.
    """

    raw_fields: dict[int, list[object]] = field(default_factory=dict)
    """
    All raw protobuf field numbers and their decoded wire values, as
    returned by the wire-format decoder.  Useful for inspecting an
    unrecognised schema or verifying field-number assignments.
    """

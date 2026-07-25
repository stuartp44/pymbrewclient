from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import struct

from .models import DecodedDeviceLogTelemetry


class ProtobufDecodeError(ValueError):
    """Raised when a protobuf message cannot be decoded safely."""


@dataclass
class _ParsedField:
    field_number: int
    wire_type: int
    value: int | float | bytes


_WIRE_TYPE_VARINT = 0
_WIRE_TYPE_FIXED64 = 1
_WIRE_TYPE_LENGTH_DELIMITED = 2
_WIRE_TYPE_FIXED32 = 5

# Field numbers observed from captured MiniBrew device-log payloads.
_FIELD_SESSION_ID = 1
_FIELD_MESSAGE_TIMESTAMP = 2
_FIELD_PROCESS_STATE = 3
_FIELD_USER_ACTION = 4
_FIELD_CURRENT_TEMPERATURE = 5
_FIELD_TARGET_TEMPERATURE = 6
_FIELD_REMAINING_DURATION_SECONDS = 7
_FIELD_SECONDS_UNTIL_NEXT_ACTION = 8


def decode_device_log_payload(payload: bytes) -> DecodedDeviceLogTelemetry:
    """Decode a MiniBrew device-log payload into typed telemetry."""
    fields = _parse_wire_fields(payload)
    telemetry = DecodedDeviceLogTelemetry()
    unknown_fields: list[int] = []

    for field in fields:
        if field.field_number == _FIELD_SESSION_ID and isinstance(field.value, int):
            telemetry.session_id = field.value
        elif field.field_number == _FIELD_MESSAGE_TIMESTAMP and isinstance(field.value, int):
            telemetry.message_timestamp = datetime.fromtimestamp(field.value, tz=timezone.utc)
        elif field.field_number == _FIELD_PROCESS_STATE and isinstance(field.value, int):
            telemetry.process_state = field.value
        elif field.field_number == _FIELD_USER_ACTION and isinstance(field.value, int):
            telemetry.user_action_state = field.value
        elif field.field_number == _FIELD_CURRENT_TEMPERATURE and isinstance(field.value, float):
            telemetry.current_temperature = field.value
        elif field.field_number == _FIELD_TARGET_TEMPERATURE and isinstance(field.value, float):
            telemetry.target_temperature = field.value
        elif field.field_number == _FIELD_REMAINING_DURATION_SECONDS and isinstance(field.value, int):
            telemetry.remaining_process_duration_seconds = field.value
        elif field.field_number == _FIELD_SECONDS_UNTIL_NEXT_ACTION and isinstance(field.value, int):
            telemetry.seconds_until_next_action = field.value
        else:
            unknown_fields.append(field.field_number)

    telemetry.unknown_fields = sorted(set(unknown_fields))

    if telemetry.message_timestamp is not None and telemetry.seconds_until_next_action is not None:
        telemetry.next_action_at = telemetry.message_timestamp + timedelta(seconds=telemetry.seconds_until_next_action)

    return telemetry


def _parse_wire_fields(payload: bytes) -> list[_ParsedField]:
    index = 0
    fields: list[_ParsedField] = []

    while index < len(payload):
        key, index = _read_varint(payload, index)
        field_number = key >> 3
        wire_type = key & 0x07

        if field_number <= 0:
            raise ProtobufDecodeError("Invalid field number in protobuf payload.")

        if wire_type == _WIRE_TYPE_VARINT:
            value, index = _read_varint(payload, index)
            fields.append(_ParsedField(field_number=field_number, wire_type=wire_type, value=value))
        elif wire_type == _WIRE_TYPE_FIXED64:
            if index + 8 > len(payload):
                raise ProtobufDecodeError("Truncated protobuf fixed64 field.")
            value = payload[index : index + 8]
            index += 8
            fields.append(_ParsedField(field_number=field_number, wire_type=wire_type, value=value))
        elif wire_type == _WIRE_TYPE_LENGTH_DELIMITED:
            size, index = _read_varint(payload, index)
            if index + size > len(payload):
                raise ProtobufDecodeError("Truncated protobuf length-delimited field.")
            value = payload[index : index + size]
            index += size
            fields.append(_ParsedField(field_number=field_number, wire_type=wire_type, value=value))
        elif wire_type == _WIRE_TYPE_FIXED32:
            if index + 4 > len(payload):
                raise ProtobufDecodeError("Truncated protobuf fixed32 field.")
            raw_value = payload[index : index + 4]
            index += 4
            value = struct.unpack("<f", raw_value)[0]
            fields.append(_ParsedField(field_number=field_number, wire_type=wire_type, value=value))
        else:
            raise ProtobufDecodeError(f"Unsupported protobuf wire type: {wire_type}.")

    return fields


def _read_varint(payload: bytes, index: int) -> tuple[int, int]:
    value = 0
    shift = 0

    while True:
        if index >= len(payload):
            raise ProtobufDecodeError("Truncated protobuf varint.")
        byte = payload[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return value, index
        shift += 7
        if shift >= 64:
            raise ProtobufDecodeError("Varint is too large.")

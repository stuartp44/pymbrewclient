from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DecodedDeviceLogTelemetry:
    session_id: int | None = None
    message_timestamp: datetime | None = None
    process_state: int | None = None
    user_action_state: int | None = None
    current_temperature: float | None = None
    target_temperature: float | None = None
    remaining_process_duration_seconds: int | None = None
    seconds_until_next_action: int | None = None
    next_action_at: datetime | None = None
    unknown_fields: list[int] = field(default_factory=list)


@dataclass
class MqttMessage:
    topic: str
    payload: bytes
    received_at: datetime
    device_uuid: str | None
    decoded_telemetry: DecodedDeviceLogTelemetry | None = None
    decoding_error: str | None = None

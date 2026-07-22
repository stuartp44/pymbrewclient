# “Commons Clause” License Condition v1.0
#
# The Software is provided to you by the Licensor under the License, as defined below, subject to the following condition.
#
# Without limiting other conditions in the License, the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.
#
# For purposes of the foregoing, “Sell” means practicing any or all of the rights granted to you under the License to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/ support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software. Any license notice or attribution required by the License must also include this Commons Clause License Condition notice.
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
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone


def parse_api_datetime(value: str | None) -> datetime | None:
    """Parse an API timestamp into a timezone-aware datetime."""
    if value in (None, ""):
        return None

    normalized_value = value.replace("Z", "+00:00")
    parsed_value = datetime.fromisoformat(normalized_value)
    if parsed_value.tzinfo is None:
        return parsed_value.replace(tzinfo=timezone.utc)
    return parsed_value


def format_duration(total_seconds: int) -> str:
    """Format seconds as H:MM:SS."""
    duration = timedelta(seconds=total_seconds)
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def datetime_to_api_string(value: datetime | None) -> str | None:
    """Serialize a timezone-aware datetime back to an API-like UTC string."""
    if value is None:
        return None

    utc_value = value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


@dataclass
class Device:
    uuid: str
    serial_number: str | None = None
    current_state: int | None = None
    process_type: int | None = None
    process_state: int | None = None
    user_action: int | None = None
    active_session: int | None = None
    connection_status: int | None = None
    last_time_online: datetime | None = None
    software_version: str | None = None
    custom_name: str | None = None
    device_type: int | None = None
    image: str | None = None
    last_process_state_change: datetime | None = None
    process_estimate_remaining: datetime | None = None
    text: str | None = None
    updating: bool = False
    title: str | None = None
    sub_title: str | None = None
    session_id: int | None = None
    status_time: int | None = None
    stage: str | None = None
    beer_name: str | None = None
    recipe_version: str | None = None
    beer_style: str | None = None
    beer_srm: str | None = None
    gravity: str | None = None
    target_temp: float | None = None
    current_temp: float | None = None
    online: bool | None = None
    needs_acid_cleaning: bool = False
    is_starting: bool | None = None

    def __post_init__(self) -> None:
        if isinstance(self.last_time_online, str):
            self.last_time_online = parse_api_datetime(self.last_time_online)
        if isinstance(self.last_process_state_change, str):
            self.last_process_state_change = parse_api_datetime(self.last_process_state_change)
        if isinstance(self.process_estimate_remaining, str):
            self.process_estimate_remaining = parse_api_datetime(self.process_estimate_remaining)

        if self.active_session is None and self.session_id is not None:
            self.active_session = self.session_id
        if self.session_id is None and self.active_session is not None:
            self.session_id = self.active_session

    def get_process_estimate_remaining_seconds(self, current_time: datetime | None = None) -> int | None:
        """Return a local snapshot of the estimated remaining time in seconds."""
        if self.process_estimate_remaining is None:
            return None

        current_utc_time = current_time or datetime.now(timezone.utc)
        if current_utc_time.tzinfo is None:
            current_utc_time = current_utc_time.replace(tzinfo=timezone.utc)
        remaining_seconds = int((self.process_estimate_remaining - current_utc_time).total_seconds())
        return max(0, remaining_seconds)

    @property
    def process_estimate_remaining_seconds(self) -> int | None:
        """Return a local snapshot of the estimated remaining time in seconds."""
        return self.get_process_estimate_remaining_seconds()

    def get_process_estimate_remaining_formatted(self, current_time: datetime | None = None) -> str | None:
        """Format the locally calculated remaining time as H:MM:SS."""
        remaining_seconds = self.get_process_estimate_remaining_seconds(current_time=current_time)
        if remaining_seconds is None:
            return None
        return format_duration(remaining_seconds)

    @property
    def process_estimate_remaining_formatted(self) -> str | None:
        """Format the locally calculated remaining time as H:MM:SS."""
        return self.get_process_estimate_remaining_formatted()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary representation."""
        data = asdict(self)
        data["last_time_online"] = datetime_to_api_string(self.last_time_online)
        data["last_process_state_change"] = datetime_to_api_string(self.last_process_state_change)
        data["process_estimate_remaining"] = datetime_to_api_string(self.process_estimate_remaining)
        data["process_estimate_remaining_seconds"] = self.process_estimate_remaining_seconds
        data["process_estimate_remaining_formatted"] = self.process_estimate_remaining_formatted
        return data

    def __getitem__(self, key: str) -> object:
        """Provide dict-like field access for backward compatibility."""
        return self.to_dict()[key]

    def __contains__(self, key: object) -> bool:
        """Provide dict-like membership checks for backward compatibility."""
        return isinstance(key, str) and key in self.to_dict()

    def get(self, key: str, default: object = None) -> object:
        """Provide dict-like get access for backward compatibility."""
        return self.to_dict().get(key, default)


@dataclass
class BreweryOverview:
    brew_clean_idle: list[Device]
    fermenting: list[Device]
    serving: list[Device]
    brew_acid_clean_idle: list[Device]

    def __post_init__(self) -> None:
        self.brew_clean_idle = _coerce_device_list(self.brew_clean_idle)
        self.fermenting = _coerce_device_list(self.fermenting)
        self.serving = _coerce_device_list(self.serving)
        self.brew_acid_clean_idle = _coerce_device_list(self.brew_acid_clean_idle)


@dataclass
class Beer:
    id: int
    name: str
    image: str | None
    style_name: str


@dataclass
class DeviceDetails:
    uuid: str
    serial_number: str
    current_state: int
    process_type: int
    process_state: int
    user_action: int
    device_type: int
    connection_status: int
    last_time_online: str
    software_version: str
    custom_name: str

    @property
    def last_time_online_at(self) -> datetime | None:
        """Return the device timestamp as a timezone-aware datetime."""
        return parse_api_datetime(self.last_time_online)


class Session:
    def __init__(
        self,
        id: int,
        profile: int,
        beer: dict,
        device: dict,
        status: int,
        session_type: int,
        pending_command_seq: int,
        pending_command_type: int,
        pending_command_error: int,
        beer_recipe_id: int,
        beer_recipe_version: str,
        brew_timestamp: float,
        original_gravity: float,
        timestamp_original_gravity: float,
        is_brewpack: bool,
    ) -> None:
        self.id = id
        self.profile = profile
        self.beer = Beer(**beer)
        self.device = DeviceDetails(**device)
        self.status = status
        self.session_type = session_type
        self.pending_command_seq = pending_command_seq
        self.pending_command_type = pending_command_type
        self.pending_command_error = pending_command_error
        self.beer_recipe_id = beer_recipe_id
        self.beer_recipe_version = beer_recipe_version
        self.brew_timestamp = brew_timestamp
        self.original_gravity = original_gravity
        self.timestamp_original_gravity = timestamp_original_gravity
        self.is_brewpack = is_brewpack

    def __repr__(self) -> str:
        return (
            f"Session(\n"
            f"  id={self.id},\n"
            f"  profile={self.profile},\n"
            f"  beer={self.beer},\n"
            f"  device={self.device},\n"
            f"  status={self.status},\n"
            f"  session_type={self.session_type},\n"
            f"  pending_command_seq={self.pending_command_seq},\n"
            f"  pending_command_type={self.pending_command_type},\n"
            f"  pending_command_error={self.pending_command_error},\n"
            f"  beer_recipe_id={self.beer_recipe_id},\n"
            f"  beer_recipe_version={self.beer_recipe_version},\n"
            f"  brew_timestamp={self.brew_timestamp},\n"
            f"  original_gravity={self.original_gravity},\n"
            f"  timestamp_original_gravity={self.timestamp_original_gravity},\n"
            f"  is_brewpack={self.is_brewpack}\n"
            f")"
        )


@dataclass
class TokenResponse:
    token: str
    exp: int


@dataclass
class ApiResponse:
    status_code: int
    data: dict | None
    message: str | None


def coerce_device_payload(device: Device | dict[str, object]) -> Device:
    """Convert device dictionaries into Device objects while filtering unknown fields."""
    if isinstance(device, Device):
        return device

    device_field_names = {field.name for field in fields(Device)}
    filtered_device = {key: value for key, value in device.items() if key in device_field_names}
    return Device(**filtered_device)


def _coerce_device_list(devices: list[Device] | list[dict[str, object]]) -> list[Device]:
    return [coerce_device_payload(device) for device in devices]

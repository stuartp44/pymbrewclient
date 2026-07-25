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
from datetime import datetime

from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.models import BreweryOverview, Device, Session, TokenResponse, UserProfile


class BreweryClientError(ValueError):
    """Base exception for BreweryClient lookup and validation errors."""


class DeviceLookupError(BreweryClientError):
    """Raised when a device cannot be resolved uniquely."""


class BreweryClient:
    """
    A client for interacting with the Minibrew Pro Portal API.
    """

    def __init__(self, username: str, password: str, base_url: str = "https://api.minibrew.io") -> None:
        """
        Initialize the client with the base URL and user credentials.

        :param base_url: The base URL for the API.
        :param username: The username for authentication.
        :param password: The password for authentication.
        """
        self.client = RestApiClient(base_url=base_url, username=username, password=password)

    def get_token(self) -> TokenResponse:
        """
        Fetch and return the authentication token.

        :return: A TokenResponse object containing the token and expiry time.
        """
        return self.client._get_token()

    def get_brewery_overview(self) -> BreweryOverview:
        """
        Fetch and return the brewery overview.

        :return: A BreweryOverview object containing the overview data.
        """
        return self.client.get_brewery_overview()

    def get_devices(self) -> list[Device]:
        """Fetch and return the authenticated device list."""
        return self.client.get_devices()

    def get_session_info(self, sessionid: int) -> Session:
        """
        Fetch and return session information for a given session ID.

        :param sessionid: The session ID to fetch information for.
        :return: A Session object containing the session data.
        """
        return self.client.get_session_info(sessionid)

    def _get_selected_device(self, device_uuid: str | None = None, session_id: int | None = None) -> Device:
        if (device_uuid is None) == (session_id is None):
            raise BreweryClientError("Provide exactly one of device_uuid or session_id.")

        devices = self.get_devices()
        if device_uuid is not None:
            matching_devices = [device for device in devices if device.uuid == device_uuid]
            if not matching_devices:
                raise DeviceLookupError(f"No device found for UUID '{device_uuid}'.")
            return matching_devices[0]

        matching_devices = [device for device in devices if device.active_session == session_id]
        if not matching_devices:
            raise DeviceLookupError(f"No device found for active session ID {session_id}.")
        if len(matching_devices) > 1:
            raise DeviceLookupError(f"Multiple devices found for active session ID {session_id}.")
        return matching_devices[0]

    def get_device(self, device_uuid: str | None = None, session_id: int | None = None) -> Device:
        """Return one authenticated device selected by UUID or active session."""
        return self._get_selected_device(device_uuid=device_uuid, session_id=session_id)

    def get_process_estimate(self, device_uuid: str | None = None, session_id: int | None = None) -> datetime | None:
        """Return MiniBrew's absolute UTC process estimate for a selected device."""
        device = self.get_device(device_uuid=device_uuid, session_id=session_id)
        return device.process_estimate_remaining

    def get_process_estimate_remaining_seconds(
        self,
        device_uuid: str | None = None,
        session_id: int | None = None,
    ) -> int | None:
        """Return a locally calculated remaining duration for a selected device."""
        device = self.get_device(device_uuid=device_uuid, session_id=session_id)
        return device.process_estimate_remaining_seconds

    def get_user_profile(self) -> UserProfile:
        """
        Fetch and return the authenticated user's profile.

        The user UUID is required to construct MQTT credentials.

        :return: A UserProfile object containing the user UUID and profile data.
        """
        return self.client.get_user_profile()

    def create_mqtt_client(self) -> "MqttClient":
        """
        Create and return a configured MQTT-over-WebSocket client.

        The current REST API token is reused as the MQTT password.  A fresh
        token is obtained if the current one has expired.  A new random
        ``client_uuid`` is generated for each call, so multiple independent
        MQTT clients can be created from the same :class:`BreweryClient`.

        .. warning::

            The API token is used as the MQTT password.  Do not log the
            returned :class:`~pymbrewclient.mqtt.MqttClient` instance in
            contexts that would reveal sensitive credentials.

        :return: A ready-to-connect :class:`~pymbrewclient.mqtt.MqttClient`.
        """
        from pymbrewclient.mqtt.client import MqttClient

        self.client._ensure_token()
        profile = self.get_user_profile()
        return MqttClient(api_token=self.client.token, user_uuid=profile.uuid)


# Local alias for the forward reference in create_mqtt_client's type hint
try:
    from pymbrewclient.mqtt.client import MqttClient  # noqa: E402, F401
except ImportError:
    pass

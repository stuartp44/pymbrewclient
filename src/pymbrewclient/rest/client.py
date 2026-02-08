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
# Disclaimer: This software is an independent project and is not affiliated with, endorsed by, or associated with MiniBrew. MiniBrew's trademarks, logos, API, and other intellectual property are owned by MiniBrew and are not included in this software. Users are responsible for complying with MiniBrew's terms of service when using this software.import requests

from typing import Any
import requests
import time
from .models import TokenResponse, ApiResponse, BreweryOverview, Session
from loguru import logger


class RestApiClient:
    def __init__(self, username: str, password: str, base_url: str, headers: dict[str, str] | None = None) -> None:
        """
        Initialize the REST API client for mbrewclient.

        :param base_url: The base URL for the API.
        :param username: The username for the Minibrew Pro Portal.
        :param password: The password for the Minibrew Pro Portal.
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.headers = {"Client": "Breweryportal", "Content-Type": "application/json"}
        self.token = None
        self.token_expiry = 0

    def _get_token(self) -> TokenResponse:
        """
        Obtain a new token using the username and password.

        :return: A TokenResponse object containing the token and expiry time.
        """
        logger.debug("Fetching new token...")
        url = "v2/token"
        token_headers = self.headers.copy()
        token_headers["Authorization"] = "TOKEN 4c433da015985d17669c604a5a4e2c906083e815"

        response = self.post(
            endpoint=url,
            json={"email": self.username, "password": self.password},
            headers=token_headers,
        )
        data = response.json()
        self.token = data["token"]
        self.token_expiry = time.time() + data["exp"]
        self.headers["Authorization"] = f"Bearer {self.token}"

        return TokenResponse(token=self.token, exp=data["exp"])

    @staticmethod
    def _mask_sensitive_payload(payload: Any) -> Any:
        if payload is None:
            return None
        sensitive_keys = {"password", "pass", "passwd", "token", "authorization", "auth", "secret"}

        def mask(value: Any) -> Any:
            if isinstance(value, dict):
                masked_dict: dict[str, Any] = {}
                for key, item in value.items():
                    if isinstance(key, str) and key.lower() in sensitive_keys:
                        masked_dict[key] = "***"
                    else:
                        masked_dict[key] = mask(item)
                return masked_dict
            elif isinstance(value, list):
                return [mask(item) for item in value]
            elif isinstance(value, tuple):
                return tuple(mask(item) for item in value)
            else:
                return value

        return mask(payload)
    def _is_token_valid(self) -> bool:
        """
        Check if the current token is still valid.

        :return: True if the token is valid, False otherwise.
        """
        if self.token is not None and time.time() < self.token_expiry:
            return True
        else:
            logger.debug("Token is invalid or expired.")
            return False

    def _ensure_token(self) -> None:
        """
        Ensure a valid token is available. Renew if necessary.

        :return: None
        """
        logger.debug("Ensuring token is valid...")
        if not self._is_token_valid():
            self._get_token()

    def get(self, endpoint: str, params: dict[str, Any] | None = None, ensure_token: bool = True) -> ApiResponse:
        """
        Perform a GET request.

        :param endpoint: The API endpoint (relative to the base URL).
        :param params: Optional query parameters.
        :return: An ApiResponse object containing the response data.
        """
        logger.debug(f"GET request to {endpoint} with params: {params}")
        if ensure_token:
            self._ensure_token()

        url = f"{self.base_url}/{endpoint}/"
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> requests.Response:
        """
        Perform a POST request.

        :param endpoint: The API endpoint (relative to the base URL).
        :param data: Optional form data to send in the body.
        :param json: Optional JSON data to send in the body.
        :return: The response object.
        """
        if logger.is_enabled("DEBUG"):
            safe_data = self._mask_sensitive_payload(data)
            safe_json = self._mask_sensitive_payload(json)
            logger.debug(
                "POST request to {} with data: {}, json: {}",
                endpoint,
                safe_data,
                safe_json,
            )
        url = f"{self.base_url}/{endpoint}/"
        response = requests.post(url, headers=headers, data=data, json=json)
        response.raise_for_status()
        return response

    def get_brewery_overview(self) -> BreweryOverview:
        """
        Fetch the BreweryOverview from the API.

        :return: A BreweryOverview object containing the brewery overview data.
        """
        logger.debug("Fetching brewery overview...")
        response = self.get("v1/breweryoverview")
        return BreweryOverview(**response.json())

    def get_session_info(self, sessionid: int) -> Session:
        """
        Fetch session information from the API.

        :param sessionid: The session ID to include in the query string.
        :return: A Session object containing the session information.
        """
        logger.debug(f"Fetching session info for session ID: {sessionid}")
        response = self.get(f"v1/sessions/{sessionid}")
        return Session(**response.json())

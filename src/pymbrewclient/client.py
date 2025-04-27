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
# Disclaimer: This software is an independent project and is not affiliated with, endorsed by, or associated with MiniBrew. MiniBrew's trademarks, logos, API, and other intellectual property are owned by MiniBrew and are not included in this software. Users are responsible for complying with MiniBrew's terms of service when using this software.from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.models import TokenResponse, BreweryOverview, Session


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

    def get_session_info(self, sessionid: int) -> Session:
        """
        Fetch and return session information for a given session ID.

        :param sessionid: The session ID to fetch information for.
        :return: A Session object containing the session data.
        """
        return self.client.get_session_info(sessionid)

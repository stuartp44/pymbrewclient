import unittest
from unittest.mock import patch, MagicMock
from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.models import TokenResponse, BreweryOverview, Beer

class TestRestApiClient(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the test environment.
        """
        self.client = RestApiClient(
            base_url="https://api.example.com",
            username="test_user",
            password="test_password"
        )

    @patch("pymbrewclient.rest.client.requests.post")
    def test_get_token(self, mock_post: MagicMock) -> None:
        """
        Test the _get_token method.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "mock_token", "exp": 3600}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token_response = self.client._get_token()

        self.assertIsInstance(token_response, TokenResponse)
        self.assertEqual(token_response.token, "mock_token")
        self.assertGreater(self.client.token_expiry, 0)
        self.assertEqual(self.client.headers["Authorization"], "Bearer mock_token")

    @patch("pymbrewclient.rest.client.RestApiClient._get_token")
    @patch("pymbrewclient.rest.client.requests.get")
    def test_get_brewery_overview(self, mock_get: MagicMock, mock_get_token: MagicMock) -> None:
        """
        Test the get_brewery_overview method.
        """
        # Mock the _get_token method to prevent live HTTP requests
        mock_get_token.return_value = None
        self.client.token = "mock_token"
        self.client.headers["Authorization"] = "Bearer mock_token"

        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "brew_clean_idle": [],
            "fermenting": [],
            "serving": [],
            "brew_acid_clean_idle": []
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the method under test
        overview = self.client.get_brewery_overview()

        # Assertions
        self.assertIsInstance(overview, BreweryOverview)
        self.assertEqual(len(overview.brew_clean_idle), 0)
        self.assertEqual(len(overview.fermenting), 0)

    @patch("time.time")
    def test_is_token_valid(self, mock_time: MagicMock) -> None:
        """
        Test the _is_token_valid method for both valid and expired tokens.
        """
        # Case 1: Token is valid
        self.client.token = "mock_token"
        self.client.token_expiry = 2000  # Token expiry time
        mock_time.return_value = 1000  # Current time
        self.assertTrue(self.client._is_token_valid(), "Token should be valid.")

        # Case 2: Token is expired
        mock_time.return_value = 3000  # Current time after expiry
        self.assertFalse(self.client._is_token_valid(), "Token should be expired.")

        # Case 3: Token is None
        self.client.token = None
        self.assertFalse(self.client._is_token_valid(), "Token should be invalid when None.")

    @patch("pymbrewclient.rest.client.RestApiClient._get_token")
    @patch("time.time")
    def test_ensure_token(self, mock_time: MagicMock, mock_get_token: MagicMock) -> None:
        """
        Test the _ensure_token method to ensure it renews the token when invalid.
        """
        # Case 1: Token is valid, _get_token should not be called
        self.client.token = "mock_token"
        self.client.token_expiry = 2000  # Token expiry time
        mock_time.return_value = 1000  # Current time
        self.client._ensure_token()
        mock_get_token.assert_not_called()

        # Case 2: Token is expired, _get_token should be called
        mock_time.return_value = 3000  # Current time after expiry
        self.client._ensure_token()
        mock_get_token.assert_called_once()

        # Case 3: Token is None, _get_token should be called
        self.client.token = None
        self.client._ensure_token()
        self.assertEqual(mock_get_token.call_count, 2)  # Called twice in total

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        """
        Test the get method to ensure it performs a GET request correctly.
        """
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the method under test
        endpoint = "test-endpoint"
        params = {"param1": "value1"}
        response = self.client.get(endpoint, params=params)

        # Assertions
        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/test-endpoint/",
            headers=self.client.headers,
            params=params
        )
        self.assertEqual(response.json(), {"key": "value"})

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_session_info(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        """
        Test the get_session_info method.
        """
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 12345,
            "profile": 67890,
            "beer": {"id": 11111, "name": "Mock Beer", "style_name": "Mock Style", "image": None},
            "device": {"uuid": "mock-uuid-12345", "serial_number": "mock-serial-12345", "current_state": 1, "process_type": 2, "process_state": 3, "user_action": 4, "device_type": 5, "connection_status": 6, "last_time_online": "2023-10-01T12:00:00Z", "software_version": "1.0.0", "custom_name": "Mock Device"},
            "status": 1,
            "session_type": 0,
            "pending_command_seq": 98765,
            "pending_command_type": 3,
            "pending_command_error": 0,
            "beer_recipe_id": 54321,
            "beer_recipe_version": "1",
            "brew_timestamp": 1743857868.656157,
            "original_gravity": None,
            "timestamp_original_gravity": None,
            "is_brewpack": False
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the method under test
        session_id = 12345
        session_info = self.client.get_session_info(session_id)

        # Assertions
        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/v1/sessions/{session_id}/",
            params=None,
            headers=self.client.headers
        )
        # Access the beer field
        beer = session_info.beer

        # Assertions
        self.assertIsInstance(beer, Beer)  # Ensure beer is a Beer object
        self.assertEqual(beer.id, 11111)
        self.assertEqual(beer.name, "Mock Beer")
        self.assertEqual(beer.style_name, "Mock Style")
        self.assertIsNone(beer.image)

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_brewery_overview_with_data(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        """
        Test the get_brewery_overview method with non-empty data.
        """
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "brew_clean_idle": [{"uuid": "device-1"}],
            "fermenting": [{"uuid": "device-2"}],
            "serving": [{"uuid": "device-3"}],
            "brew_acid_clean_idle": [{"uuid": "device-4"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the method under test
        overview = self.client.get_brewery_overview()

        # Assertions
        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/v1/breweryoverview/",
            params=None,
            headers=self.client.headers
        )
        self.assertIsInstance(overview, BreweryOverview)
        self.assertEqual(len(overview.brew_clean_idle), 1)
        self.assertEqual(len(overview.fermenting), 1)
        self.assertEqual(len(overview.serving), 1)
        self.assertEqual(len(overview.brew_acid_clean_idle), 1)

    @patch("pymbrewclient.rest.client.requests.post")
    def test_get_token_error(self, mock_post: MagicMock) -> None:
        """
        Test the _get_token method when the API returns an error.
        """
        # Mock the response from requests.post
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API error")
        mock_post.return_value = mock_response

        # Call the method under test and assert it raises an exception
        with self.assertRaises(Exception) as context:
            self.client._get_token()
        self.assertEqual(str(context.exception), "API error")
        mock_post.assert_called_once()

if __name__ == "__main__":
    unittest.main()
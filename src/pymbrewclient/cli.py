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
from dataclasses import asdict, is_dataclass
from datetime import datetime
import json
import logging
from typing import Annotated

import typer
from pydantic import BaseModel
from rich import print as rich_print
from rich.pretty import Pretty

from pymbrewclient.client import BreweryClient, BreweryClientError
from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.models import Device, datetime_to_api_string, format_duration

logger = logging.getLogger(__name__)

app = typer.Typer(help="CLI for reading information from the Minibrew Pro Portal.", no_args_is_help=True)

base_url = "https://api.minibrew.io"


def initialize_client(base_url: str, username: str, password: str) -> RestApiClient:
    """
    Initialize the RestApiClient with the provided credentials.
    """
    return RestApiClient(base_url=base_url, username=username, password=password)


def initialize_brewery_client(base_url: str, username: str, password: str) -> BreweryClient:
    """Initialize the BreweryClient with the provided credentials."""
    return BreweryClient(base_url=base_url, username=username, password=password)


def serialize_output(data: object) -> object:
    """Convert output to JSON-serializable primitives."""
    if isinstance(data, BaseModel):
        return serialize_output(data.dict())
    if isinstance(data, datetime):
        return datetime_to_api_string(data)
    if isinstance(data, Device):
        return data.to_dict()
    if is_dataclass(data):
        return serialize_output(asdict(data))
    if isinstance(data, dict):
        return {key: serialize_output(value) for key, value in data.items()}
    if isinstance(data, list):
        return [serialize_output(item) for item in data]
    if hasattr(data, "to_dict"):
        return serialize_output(data.to_dict())
    if hasattr(data, "__dict__"):
        return serialize_output(vars(data))
    return data


def print_output(data: BaseModel | dict | list, format: str) -> None:
    """Print output in the specified format."""
    serialized_data = serialize_output(data)

    if format == "json":
        typer.echo(json.dumps(serialized_data, indent=4))
    else:
        rich_print(Pretty(serialized_data))


def setup_logging(level: str) -> None:
    """Configure standard logging with the specified log level."""
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s", force=True)


@app.callback()
def configure(
    logging_level: Annotated[
        str,
        typer.Option(
            "--logging-level",
            help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            case_sensitive=False,
        ),
    ] = "INFO",
) -> None:
    """
    CLI for reading information from the MiniBrew Pro Portal.
    """
    setup_logging(logging_level)


@app.command()
def get_token(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display the token.
    """
    try:
        logger.info("Fetching token...")
        client = initialize_client(base_url, username, password)
        token_response = client._get_token()
        print_output(token_response, "pretty")
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
        typer.echo(f"Error fetching token: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_brewery_overview(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display the brewery overview.
    """
    try:
        logger.info("Fetching brewery overview...")
        client = initialize_client(base_url, username, password)
        overview = client.get_brewery_overview()
        print_output(overview, "pretty")
    except Exception as e:
        logger.error(f"Error fetching brewery overview: {e}")
        typer.echo(f"Error fetching brewery overview: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_session_info(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
    sessionid: int = typer.Option(..., "--sessionid", help="The session ID to fetch information for."),
) -> None:
    """
    Fetch and display session information.
    """
    try:
        logger.info(f"Fetching session info for session ID: {sessionid}...")
        client = initialize_client(base_url, username, password)
        session = client.get_session_info(sessionid)
        print_output(session, "pretty")
    except Exception as e:
        logger.error(f"Error fetching session info: {e}")
        typer.echo(f"Error fetching session info: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_fermenting(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display fermenting devices.
    """
    try:
        logger.info("Fetching fermenting devices...")
        client = initialize_client(base_url, username, password)
        overview = client.get_brewery_overview()
        print_output(overview.fermenting, "pretty")
    except Exception as e:
        logger.error(f"Error fetching fermenting devices: {e}")
        typer.echo(f"Error fetching fermenting devices: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_serving(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display serving devices.
    """
    try:
        logger.info("Fetching serving devices...")
        client = initialize_client(base_url, username, password)
        overview = client.get_brewery_overview()
        print_output(overview.serving, "pretty")
    except Exception as e:
        logger.error(f"Error fetching serving devices: {e}")
        typer.echo(f"Error fetching serving devices: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_brew_clean_idle(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display brew clean idle devices.
    """
    try:
        client = initialize_client(base_url, username, password)
        overview = client.get_brewery_overview()
        print_output(overview.brew_clean_idle, "pretty")
    except Exception as e:
        logger.error(f"Error fetching brew clean idle devices: {e}")
        typer.echo(f"Error fetching brew clean idle devices: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_brew_acid_clean_idle(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display brew acid clean idle devices.
    """
    try:
        client = initialize_client(base_url, username, password)
        overview = client.get_brewery_overview()
        print_output(overview.brew_acid_clean_idle, "pretty")
    except Exception as e:
        logger.error(f"Error fetching brew acid clean idle devices: {e}")
        typer.echo(f"Error fetching brew acid clean idle devices: {e}")
        raise typer.Exit(code=1)


@app.command()
def get_minibrew_devices(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
) -> None:
    """
    Fetch and display all devices.
    """
    try:
        logger.info("Fetching all devices...")
        client = initialize_brewery_client(base_url, username, password)
        devices = client.get_devices()
        unique_devices = list({device.uuid: device for device in devices if device.uuid is not None}.values())

        selected_data = [
            {
                "Serial Number": device.serial_number,
                "Nickname": device.custom_name or device.title,
                "Version": device.software_version,
                "Is online": device.online,
                "Stage": device.stage,
            }
            for device in unique_devices
        ]
        print_output(selected_data, "pretty")
    except Exception as e:
        logger.error(f"Error fetching all devices: {e}")
        typer.echo(f"Error fetching all devices: {e}")
        raise typer.Exit(code=1)


@app.command()
def process_estimate(
    username: str = typer.Option(..., "--username", help="The username for authentication."),
    password: str = typer.Option(..., "--password", help="The password for authentication."),
    base_url: str = typer.Option(base_url, "--base-url", help="The base URL for the API."),
    device_uuid: str | None = typer.Option(None, "--device-uuid", help="The device UUID to query."),
    session_id: int | None = typer.Option(None, "--session-id", help="The active session ID to query."),
    output_format: str = typer.Option("pretty", "--format", help="Output format: pretty or json."),
) -> None:
    """Fetch MiniBrew's REST process estimate for one device."""
    try:
        client = initialize_brewery_client(base_url, username, password)
        device = client.get_device(device_uuid=device_uuid, session_id=session_id)
        estimate = device.process_estimate_remaining
        remaining_seconds = device.process_estimate_remaining_seconds
        remaining_formatted = format_duration(remaining_seconds) if remaining_seconds is not None else None
        payload = {
            "process_estimate_remaining": datetime_to_api_string(estimate),
            "process_estimate_remaining_seconds": remaining_seconds,
            "process_estimate_remaining_formatted": remaining_formatted,
            "warning": (
                "MiniBrew provides this as an absolute UTC estimate via REST. Remaining values are calculated "
                "locally and may be stale or already in the past."
            ),
        }
        print_output(payload, output_format.lower())
    except BreweryClientError as e:
        logger.error(f"Error fetching process estimate: {e}")
        typer.echo(f"Error fetching process estimate: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error fetching process estimate: {e}")
        typer.echo(f"Error fetching process estimate: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

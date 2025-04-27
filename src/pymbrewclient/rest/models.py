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
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Device:
    uuid: str
    serial_number: str
    device_type: int
    user_action: int
    process_type: int
    title: str
    sub_title: str
    session_id: Optional[int]
    image: str
    status_time: Optional[int]
    stage: str
    beer_name: Optional[str]
    recipe_version: Optional[str]
    beer_style: Optional[str]
    gravity: str
    target_temp: Optional[float]
    current_temp: Optional[float]
    online: bool
    updating: bool
    needs_acid_cleaning: bool
    is_starting: Optional[bool]
    software_version: str

@dataclass
class BreweryOverview:
    brew_clean_idle: List[Device]
    fermenting: List[Device]
    serving: List[Device]
    brew_acid_clean_idle: List[Device]

@dataclass
class Beer:
    id: int
    name: str
    image: Optional[str]
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
    ):
        self.id = id
        self.profile = profile
        self.beer = Beer(**beer)  # Convert the beer dictionary into a Beer object
        self.device = DeviceDetails(**device)  # Convert the device dictionary into a DeviceDetails object
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
    
    def __repr__(self):
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
    data: Optional[dict]
    message: Optional[str]
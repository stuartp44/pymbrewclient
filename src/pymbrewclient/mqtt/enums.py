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
Enumerations for the MiniBrew MQTT/protobuf telemetry.

These mirror the ``MachineType``, ``MachineConnectionStatus``, ``SensorType``,
and ``ActuatorType`` enums from MiniBrew's compiled protobuf client. Values are
reproduced verbatim so decoded integers can be mapped to meaningful names.

Notably, the repeated ``measurements`` in a device-log telemetry message are
keyed by :class:`SensorType`. For example ``SensorType.TEMP_LIQUID`` (3) is the
current liquid temperature and ``SensorType.TEMP_CONTROL_POWER`` (24) is the
Peltier heating/cooling power as a signed percentage (negative = cooling).

``SensorType.GSENSOR_RSSI`` (27) is the signal strength of an *external* gravity
sensor, not the machine's own Wi-Fi; it reads ``0`` when no such sensor is
attached.
"""

from enum import IntEnum


class MachineType(IntEnum):
    """The kind of MiniBrew machine reporting telemetry."""

    BASE = 0
    KEG = 1


class MachineConnectionStatus(IntEnum):
    """A machine's cloud connection state."""

    OFFLINE = 0
    ONLINE = 1
    NOT_RESPONDING = 2


class SensorType(IntEnum):
    """
    Sensor/measurement channel identifiers.

    Device-log ``measurements`` are keyed by these values. Gaps in the numbering
    (5, 8, 11) mirror the source enum and have no assigned sensor.
    """

    TEMP_ENVIRONMENT = 0
    TEMP_CONTROL_OUT = 1
    TEMP_CONTROL_IN = 2
    TEMP_LIQUID = 3
    TEMP_PELTIER = 4
    PUMP_CURRENT = 6
    CAROUSSEL_POSITION = 7
    TOP_CONNECTION_PRESENT = 9
    BOTTOM_CONNECTION_PRESENT = 10
    CAROUSEL_ZERO_POSITION = 12
    ESP_CORE_TEMP = 13
    BAROMETRIC_PRESSURE = 14
    VALVE_MASH_TUN_OPEN = 15
    VALVE_BOILING_KETTLE_OPEN = 16
    VALVE_WATER_INLET_OPEN = 17
    SYSTEM_TEMP = 18
    BUTTON = 19
    PCB_FAN = 20
    GSENSOR_TEMP = 21
    GSENSOR_GRAVITY = 22
    GSENSOR_BATTERY = 23
    TEMP_CONTROL_POWER = 24
    LIQUID_FLOW_POWER = 25
    PELTIER_FAN_POWER = 26
    GSENSOR_RSSI = 27


class ActuatorType(IntEnum):
    """Controllable actuators on a MiniBrew machine."""

    UNUSED = 0
    VALVE_TO_MASHING_TUN = 2
    VALVE_TO_BOILING_KETTLE = 3
    VALVE_WATER_INLET = 4
    FAN_PCB = 5


class ProcessType(IntEnum):
    """Top-level process currently running on the MiniBrew machine."""

    PROC_IDLE = 0
    PROC_BREWING = 1
    PROC_CLEAN_MINIBREW = 2
    PROC_CLEAN_KEG = 3
    PROC_ACID_CLEAN_MINIBREW = 6
    PROC_FERMENTATION = 4
    PROC_SERVING = 5


class ProcessPhase(IntEnum):
    """High-level phase grouping within a process."""

    PHASE_NONE = 0
    BREW_PREPARING = 1
    BREW_MASHING = 2
    BREW_BOILING = 3
    BREW_CHILLING = 4
    FERM_PREPARING = 12
    FERM_PRIMARY = 5
    FERM_SECONDARY = 6
    FERM_CLARIFICATION = 7
    FERM_CARBONATING = 13
    SERV_SERVING = 8
    CLEAN_MB_PREPARING = 9
    CLEAN_MB_CLEANING = 10
    CLEAN_MB_RINSING = 11
    ACID_CLEAN_MB_SOAKING = 14
    ACID_CLEAN_MB_CLEANING = 15
    ACID_CLEAN_MB_RINSING = 16


class ProcessState(IntEnum):
    """Detailed machine state within process execution."""

    IDLE_STATE = 0
    MANUAL_CONTROL_STATE = 5
    PREPARE_RINSE_STATE = 6
    PUMP_PRIMING_STATE = 10
    CHECK_FLOW_STATE = 11
    CHECK_WATER_STATE = 8
    HEATUP_RINSE_STATE = 12
    CLEAN_BALL_VALVE_STATE = 13
    RINSE_BOILING_PATH_STATE = 14
    RINSE_MASHING_PATH_STATE = 15
    RINSE_COOL_STATE = 18
    RINSE_DONE_STATE = 16
    RINSE_FLOW_RECOVERY_STATE = 9
    CHECK_KEG_STATE = 7
    FILL_MACHINE_STATE = 17
    MASHBED_HYDRATE_HEATING_STATE = 20
    MASHBED_HYDRATE_FLOW_STATE = 21
    MASHBED_HYDRATE_STATE = 22
    MASHBED_HYDRATE_SETTLE_STATE = 23
    MASH_IN_STATE = 24
    MASHING_HEATUP_STATE = 30
    MASHING_MAINTAIN_STATE = 31
    MASHING_REST_STATE = 32
    MASH_LINE_FLOW_RECOVERY_STATE = 33
    SPARGING_STATE = 39
    LAUTERING_STATE = 40
    REPLACE_MASH_STATE = 43
    BOILING_HEATUP_STATE = 50
    BOILING_MAINTAIN_STATE = 51
    SECONDARY_LAUTERING_STATE = 52
    BOIL_LINE_FLOW_RECOVERY_STATE = 53
    CONNECT_WATER_STATE = 59
    COOL_WORT_STATE = 60
    FILTER_COLD_CRASH_STATE = 61
    WRITE_KEG_STATE = 65
    BREWING_DONE_STATE = 70
    BREWING_FAILED_STATE = 71
    PITCH_COOLING_STATE = 74
    PAIR_GRAVITY_SENSOR_STATE = 85
    PREPARE_FERMENTATION_STATE = 75
    FERMENTATION_TEMP_CONTROL_STATE = 80
    PLACE_AIRLOCK_STATE = 76
    REMOVE_AIRLOCK_STATE = 77
    PLACE_TRUB_CONTAINER_STATE = 78
    REMOVE_TRUB_STATE = 81
    FERMENTATION_ADD_INGREDIENT_STATE = 82
    FERMENTATION_REMOVE_INGREDIENT_STATE = 83
    FERMENTATION_FAILED_STATE = 84
    CARBONATING_STATE = 94
    PREPARE_SERVING_STATE = 88
    COOL_BEFORE_SERVING_STATE = 90
    MOUNT_TAP_STATE = 91
    SERVING_TEMP_CONTROL_STATE = 92
    SERVING_FAILED_STATE = 93
    PREPARE_CIP_STATE = 101
    DRAIN_STATE = 102
    CIP_HEATUP_STATE = 103
    PLACE_CIP_ACCESORIES_STATE = 105
    CIP_DONE_STATE = 108
    CIP_FAILED_STATE = 109
    CIRCULATE_BOILING_PATH_STATE = 111
    CIRCULATE_MASHING_PATH_STATE = 112
    RINSE_COUNTERFLOW_BOIL_STATE = 113
    RINSE_COUNTERFLOW_MASHTUN_STATE = 114
    CLEANING_FLOW_RECOVERY_STATE = 115
    CIP_SOAK_STATE = 116
    PREPARE_ACID_CLEAN_STATE = 117
    ACID_SOAK_STATE = 118
    ACID_CIRCULATE_BOILING_PATH_STATE = 119
    CLEAN_FILTER_STATE = 120
    ACID_CIRCULATE_MASHING_PATH_STATE = 121
    ACID_RINSE_BOILING_PATH_STATE = 122
    ACID_RINSE_MASHING_PATH_STATE = 123
    ACID_CLEAN_DONE_STATE = 124
    ACID_CLEAN_FAILED_STATE = 125
    ACID_CLEAN_FLOW_RECOVERY_STATE = 126


class ErrorType(IntEnum):
    """Error and warning codes reported by MiniBrew firmware."""

    ERR_UNDEFINED = 0
    ERR_IO_COMMUNICATION_FAILED = 9
    ERR_IO_COMMUNICATION_ERROR = 116
    ERR_RECIPE_INVALID = 10
    ERR_NFC_NOT_CONNECTED = 11
    ERR_NFC_READ_ERROR = 12
    ERR_NFC_WRITE_ERROR = 17
    ERR_PRESSURE_SENSOR_FAILED = 18
    ERR_MEMORY_LOW = 13
    ERR_STORAGE_LOW = 14
    ERR_FILESYSTEM_CORRUPT = 15
    ERR_I0_ENVIRONMENT_TEMP_READING_FAILED = 101
    ERR_I0_LIQUID_TEMP_CONTROL_IN_READING_FAILED = 102
    ERR_I0_LIQUID_TEMP_CONTROL_OUT_READING_FAILED = 103
    ERR_I0_LIQUID_TEMP_CONTROL_FAILED = 104
    ERR_I0_LIQUID_TEMP_CONTROL_THERMAL_PROTECTION = 105
    ERR_I0_LIQUID_PUMP_CONTROL_FAILED = 106
    ERR_I0_LIQUID_PUMP_RUNNING_DRY = 107
    ERR_I0_LIQUID_PUMP_MALFUNCTIONING = 112
    ERR_I0_LIQUID_PUMP_LOW_CURRENT_WARNING = 119
    ERR_I0_LIQUID_PUMP_HIGH_CURRENT_WARNING = 120
    ERR_IO_LIQUID_LOW_FLOW_WARNING = 117
    ERR_IO_LIQUID_INSUFFICIENT_FLOW = 118
    ERR_I0_MASH_TUN_VALVE_CONTROL_FAILED = 108
    ERR_I0_BOILING_KETTLE_VALVE_CONTROL_FAILED = 109
    ERR_I0_CAROUSEL_CONTROL_FAILED = 110
    ERR_I0_INLET_VALVE_CONTROL_FAILED = 111
    ERR_IO_LIQUID_TEMP_READING_FAILED = 113
    ERR_IO_PELTIER_TEMP_READING_FAILED = 114
    ERR_IO_AC_DETECT_FAILED = 115


class UserAction(IntEnum):
    """User interaction prompts/actions emitted by MiniBrew process state."""

    ACTION_UNDEFINED = 0
    ACTION_ADD_BREW_WATER = 1
    ACTION_PREPARE_CLEANING = 2
    ACTION_CHECK_ACTIVITY_STARTED = 3
    ACTION_ADD_INGREDIENT = 4
    ACTION_REMOVE_INGREDIENT = 5
    ACTION_CONNECT_WATER = 6
    ACTION_PLACE_KEG = 7
    ACTION_REMOVE_TRUB = 8
    ACTION_CHECK_ACTIVITY_STOPPED = 9
    ACTION_MOUNT_TAP = 10
    ACTION_REMOVE_KEG = 11
    ACTION_NEEDS_CLEANING = 12
    ACTION_BREWING_FAILED = 13
    ACTION_PREPARE_RINSING = 15
    ACTION_ADD_RINSE_WATER = 16
    ACTION_CLEAN_BALLVALVE = 17
    ACTION_EMPTY_KEG = 18
    ACTION_FILL_MASH_TUN = 19
    ACTION_FILL_CAROUSEL = 20
    ACTION_START_BREWING = 21
    ACTION_MANUAL_SPARGE = 22
    ACTION_REPLACE_MASH = 23
    ACTION_PLACE_CARROUSEL = 24
    ACTION_RESUME_BREWING = 25
    ACTION_PREPARE_FERMENTATION = 26
    ACTION_PLACE_AIRLOCK = 28
    ACTION_REMOVE_AIRLOCK = 29
    ACTION_PLACE_TRUB_CONTAINER = 30
    ACTION_CONNECT_PRESSURIZER = 31
    ACTION_START_CLEANING = 32
    ACTION_FERMENTATION_FAILED = 33
    ACTION_SERVING_FAILED = 34
    ACTION_CLEAN_MINIBREW_FAILED = 35
    ACTION_PAIR_GRAVITY_SENSOR = 36
    ACTION_FINISH_CLEANING = 37
    ACTION_KEG_NEEDS_CLEANING = 38
    ACTION_CHECK_KEG_PRESENCE = 39
    ACTION_CHECK_BALLVALVE = 40
    ACTION_CHECK_RINSE_CONNECTOR = 41
    ACTION_CHECK_INLET_WATER = 42
    ACTION_CHECK_KEG_EMPTY = 43
    ACTION_CHECK_RINSE_FLOW = 44
    ACTION_CHECK_MASH_TUN = 45
    ACTION_CHECK_CAROUSEL = 46
    ACTION_CHECK_MASH_LINE_FLOW = 47
    ACTION_CHECK_BOIL_LINE_FLOW = 48
    ACTION_CHECK_CIP_CONTAINER = 49
    ACTION_CHECK_CIP_LINES = 50
    ACTION_CHECK_CLEANING_FLOW = 51
    ACTION_PLACE_CORRECT_KEG = 52
    ACTION_PLACE_BLOW_OFF = 53
    ACTION_REMOVE_BLOW_OFF = 54
    ACTION_CHECK_CAROUSEL_JAM = 55
    ACTION_PREPARE_ACID_CLEANING = 56
    ACTION_CLEAN_CIP_FILTER = 57
    ACTION_CHECK_ACID_CLEANING_FLOW = 58
    ACTION_ACID_CLEAN_MINIBREW_FAILED = 59
    ACTION_FINISH_ACID_CLEANING = 60
    ACTION_BREWING_FAILED_PERFORM_ACID_CLEAN = 61
    ACTION_CLEAN_MINIBREW_FAILED_PERFORM_ACID_CLEAN = 62
    ACTION_NEEDS_ACID_CLEANING = 63
    ACTION_KEG_NEEDS_UPDATE = 64
    ACTION_CHECK_CARBONATION = 65
    ACTION_REPLACE_MASH_TUN = 66
    ACTION_MAX_COOLING_DURATION_ELAPSED = 67

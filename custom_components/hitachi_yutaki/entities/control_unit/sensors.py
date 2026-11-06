"""Control unit sensor descriptions and builders (outdoor + diagnostics)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from ...const import DEVICE_CONTROL_UNIT
from ..base.sensor import (
    HitachiYutakiSensor,
    HitachiYutakiSensorEntityDescription,
    _create_sensors,
)

if TYPE_CHECKING:
    from ...coordinator import HitachiYutakiDataCoordinator


def build_control_unit_sensors(
    coordinator: HitachiYutakiDataCoordinator,
    entry_id: str,
) -> list[HitachiYutakiSensor]:
    """Build control unit sensor entities (outdoor + diagnostics)."""
    descriptions = _build_control_unit_sensor_descriptions()
    return _create_sensors(coordinator, entry_id, descriptions, DEVICE_CONTROL_UNIT)


def _alarm_attributes(
    coordinator: HitachiYutakiDataCoordinator,
) -> dict[str, int] | None:
    """Expose the alarm code only while an alarm is present."""
    if coordinator.data is None:
        return None
    code = coordinator.data.get("alarm_code")
    return {"code": code} if code is not None and code != 0 else None


def _operation_state_attributes(
    coordinator: HitachiYutakiDataCoordinator,
) -> dict[str, int] | None:
    """Expose the raw operation code, including the valid off code zero."""
    if coordinator.data is None:
        return None
    code = coordinator.data.get("operation_state_code")
    return {"code": code} if code is not None else None


def _build_control_unit_sensor_descriptions() -> tuple[
    HitachiYutakiSensorEntityDescription, ...
]:
    """Build control unit sensor descriptions."""
    return (
        # Outdoor sensors
        HitachiYutakiSensorEntityDescription(
            key="outdoor_temp",
            translation_key="outdoor_temp",
            description="Outdoor ambient temperature measurement",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda coordinator: coordinator.data.get("outdoor_temp"),
        ),
        # Diagnostics sensors (alarm, operation_state only - power_consumption moved to power/)
        HitachiYutakiSensorEntityDescription(
            key="alarm",
            translation_key="alarm",
            description="Current alarm",
            device_class=SensorDeviceClass.ENUM,
            state_class=None,
            value_fn=lambda coordinator: coordinator.data.get("alarm_code"),
            attributes_fn=_alarm_attributes,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:alert-circle-outline",
        ),
        HitachiYutakiSensorEntityDescription(
            key="operation_state",
            translation_key="operation_state",
            description="Current operation state of the heat pump",
            value_fn=lambda coordinator: coordinator.data.get("operation_state"),
            attributes_fn=_operation_state_attributes,
            icon="mdi:state-machine",
        ),
        # --- ComAp fork extras (parity with previous native YAML setup) ---
        HitachiYutakiSensorEntityDescription(
            key="circuit1_wireless_target_temp",
            translation_key="circuit1_wireless_target_temp",
            description="Circuit 1 wireless thermostat target temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("circuit1_wireless_target_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="circuit1_wireless_current_temp",
            translation_key="circuit1_wireless_current_temp",
            description="Circuit 1 wireless thermostat current temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("circuit1_wireless_current_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="circuit2_wireless_target_temp",
            translation_key="circuit2_wireless_target_temp",
            description="Circuit 2 wireless thermostat target temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("circuit2_wireless_target_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="circuit2_wireless_current_temp",
            translation_key="circuit2_wireless_current_temp",
            description="Circuit 2 wireless thermostat current temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("circuit2_wireless_current_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="outdoor_average_temp",
            translation_key="outdoor_average_temp",
            description="Averaged outdoor ambient temperature (Ta2)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("outdoor_average_temp"),
        ),
        HitachiYutakiSensorEntityDescription(
            key="second_ambient_temp",
            translation_key="second_ambient_temp",
            description="Second ambient temperature sensor",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("second_ambient_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="second_ambient_average_temp",
            translation_key="second_ambient_average_temp",
            description="Averaged second ambient temperature (Ta3)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("second_ambient_average_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="unit_capacity",
            translation_key="unit_capacity",
            description="Unit capacity reported by the heat pump",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_fn=lambda c: c.data.get("unit_capacity"),
        ),
        HitachiYutakiSensorEntityDescription(
            key="mixing_valve_position",
            translation_key="mixing_valve_position",
            description="Mixing valve position (MVP)",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            value_fn=lambda c: c.data.get("mixing_valve_position"),
            icon="mdi:pipe-valve",
        ),
        HitachiYutakiSensorEntityDescription(
            key="cause_of_stoppage",
            translation_key="cause_of_stoppage",
            description="Cause of the last compressor stoppage (DI code)",
            value_fn=lambda c: c.data.get("cause_of_stoppage"),
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:stop-circle-outline",
        ),
        HitachiYutakiSensorEntityDescription(
            key="capacity_data",
            translation_key="capacity_data",
            description="Capacity data (CD) diagnostic value",
            value_fn=lambda c: c.data.get("capacity_data"),
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="defrost_state_raw",
            translation_key="defrost_state_raw",
            description="Defrost state reported by the unit (register 1217)",
            value_fn=lambda c: (
                None
                if c.data.get("defrost_state_raw") is None
                else (
                    "defrosting" if c.data.get("defrost_state_raw") else "no_defrosting"
                )
            ),
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:snowflake-melt",
        ),
        HitachiYutakiSensorEntityDescription(
            key="software_pcb",
            translation_key="software_pcb",
            description="PCB software version",
            value_fn=lambda c: c.data.get("software_pcb"),
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:chip",
        ),
        HitachiYutakiSensorEntityDescription(
            key="software_lcd",
            translation_key="software_lcd",
            description="LCD software version",
            value_fn=lambda c: c.data.get("software_lcd"),
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:chip",
        ),
        HitachiYutakiSensorEntityDescription(
            key="water_outlet_unit_temp",
            translation_key="water_outlet_unit_temp",
            description="Water outlet temperature at the unit (register 1093)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("water_outlet_unit_temp"),
            entity_registry_enabled_default=False,
        ),
        HitachiYutakiSensorEntityDescription(
            key="dhw_tank_upper_temp",
            translation_key="dhw_tank_upper_temp",
            description="DHW tank upper temperature (register 1224)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("dhw_tank_upper_temp"),
        ),
        HitachiYutakiSensorEntityDescription(
            key="dhw_tank_lower_temp",
            translation_key="dhw_tank_lower_temp",
            description="DHW tank lower temperature (register 1225) — DHW charge reference",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("dhw_tank_lower_temp"),
        ),
        # ComAp fork: expose DHW current (WSP, reg 1080) and target (reg 1077)
        # as standalone sensors too (already on the water_heater as current/
        # target, but the graphic uses standalone sensor entities).
        HitachiYutakiSensorEntityDescription(
            key="dhw_wsp_temp",
            translation_key="dhw_wsp_temp",
            description="DHW temperature at the WSP sensor (register 1080)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("dhw_current_temp"),
        ),
        HitachiYutakiSensorEntityDescription(
            key="dhw_setting_temp",
            translation_key="dhw_setting_temp",
            description="DHW setpoint temperature (register 1077)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("dhw_target_temp"),
        ),
        # ComAp fork: circuit 1 room/current + thermostat setpoint as standalone
        # sensors (also on the climate as current/target; used on other dashboards).
        HitachiYutakiSensorEntityDescription(
            key="circuit1_room_temp",
            translation_key="circuit1_room_temp",
            description="Circuit 1 room temperature (register 1061)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("circuit1_current_temp"),
        ),
        HitachiYutakiSensorEntityDescription(
            key="circuit1_thermostat_set_temp",
            translation_key="circuit1_thermostat_set_temp",
            description="Circuit 1 thermostat setpoint (register 1060)",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda c: c.data.get("circuit1_target_temp"),
        ),
        HitachiYutakiSensorEntityDescription(
            key="unit_model_name",
            translation_key="unit_model_name",
            description="Unit model (register 1218)",
            value_fn=lambda c: c.data.get("unit_model"),
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:heat-pump-outline",
        ),
        HitachiYutakiSensorEntityDescription(
            key="central_mode",
            translation_key="central_mode",
            description="Central control mode (register 1088)",
            value_fn=lambda c: c.data.get("central_control_mode"),
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:tune",
        ),
        HitachiYutakiSensorEntityDescription(
            key="system_status_raw",
            translation_key="system_status_raw",
            description="Raw system status bitfield (register 1222)",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda c: c.data.get("system_status"),
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:list-status",
        ),
        HitachiYutakiSensorEntityDescription(
            key="system_config_raw",
            translation_key="system_config_raw",
            description="Raw system configuration bitfield (register 1089)",
            value_fn=lambda c: c.data.get("system_config"),
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:cog-outline",
        ),
    )

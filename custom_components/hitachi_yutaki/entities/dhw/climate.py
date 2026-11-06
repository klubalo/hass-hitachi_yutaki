"""DHW climate entity (ComAp fork).

Exposes domestic hot water as a climate entity (heat/off + target temperature)
in addition to the native water_heater, so a thermostat card / scheduler that
expects a climate entity can drive DHW (parity with the previous Modbus climate
``climate.tc_termostat_tuv``). Reads/writes the same DHW registers as the
water_heater via the API client's DHW getters/setters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ...const import DEVICE_DHW, DOMAIN
from ...coordinator import HitachiYutakiDataCoordinator

if TYPE_CHECKING:
    pass


@dataclass
class HitachiYutakiDhwClimateEntityDescription(ClimateEntityDescription):
    """Describes a Hitachi Yutaki DHW climate entity."""

    key: str = "dhw_climate"
    translation_key: str = "dhw_climate"


class HitachiYutakiDhwClimate(
    CoordinatorEntity[HitachiYutakiDataCoordinator], ClimateEntity
):
    """DHW presented as a climate entity (heat/off + target temperature)."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: HitachiYutakiDataCoordinator,
        description: HitachiYutakiDhwClimateEntityDescription,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the DHW climate entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_dhw_climate"
        self._attr_device_info = device_info
        overrides = coordinator.profile.entity_overrides.get("dhw", {})
        self._attr_min_temp = overrides.get("min_temp", 30.0)
        self._attr_max_temp = overrides.get("max_temp", 60.0)
        self._attr_target_temperature_step = overrides.get("temp_step", 1.0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_temperature(self) -> float | None:
        """Return the current DHW temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.api_client.get_dhw_current_temperature()

    @property
    def target_temperature(self) -> float | None:
        """Return the target DHW temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.api_client.get_dhw_target_temperature()

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current hvac mode (heat/off)."""
        if self.coordinator.data is None:
            return None
        return (
            HVACMode.HEAT
            if self.coordinator.api_client.get_dhw_power()
            else HVACMode.OFF
        )

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current hvac action."""
        if self.coordinator.data is None:
            return None
        if not self.coordinator.api_client.get_dhw_power():
            return HVACAction.OFF
        if self.coordinator.api_client.is_compressor_running:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new DHW target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.coordinator.api_client.set_dhw_target_temperature(temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn DHW on (heat) or off."""
        await self.coordinator.api_client.set_dhw_power(hvac_mode != HVACMode.OFF)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn DHW on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn DHW off."""
        await self.async_set_hvac_mode(HVACMode.OFF)


def build_dhw_climate(
    coordinator: HitachiYutakiDataCoordinator,
    entry_id: str,
) -> HitachiYutakiDhwClimate | None:
    """Build the DHW climate entity if DHW is configured."""
    if not coordinator.has_dhw():
        return None
    device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{DEVICE_DHW}")})
    return HitachiYutakiDhwClimate(
        coordinator=coordinator,
        description=HitachiYutakiDhwClimateEntityDescription(),
        device_info=device_info,
    )

"""DHW switch descriptions and builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...const import DEVICE_DHW
from ..base.switch import (
    HitachiYutakiSwitch,
    HitachiYutakiSwitchEntityDescription,
    _create_switches,
)

if TYPE_CHECKING:
    from ...coordinator import HitachiYutakiDataCoordinator


def build_dhw_switches(
    coordinator: HitachiYutakiDataCoordinator,
    entry_id: str,
) -> list[HitachiYutakiSwitch]:
    """Build DHW switch entities."""
    descriptions = _build_dhw_switch_descriptions()
    return _create_switches(coordinator, entry_id, descriptions, DEVICE_DHW, "dhw")


def _build_dhw_switch_descriptions() -> tuple[
    HitachiYutakiSwitchEntityDescription, ...
]:
    """Build DHW switch descriptions."""
    return (
        HitachiYutakiSwitchEntityDescription(
            key="boost",
            name="Boost",
            icon="mdi:flash",
            condition=lambda c: c.has_dhw() and c.api_client.can_write("dhw_boost"),
            get_fn=lambda api, _: api.get_dhw_boost(),
            set_fn=lambda api, _, enabled: api.set_dhw_boost(enabled),
        ),
        # ComAp fork: high-demand mode switch (register 1079/1027) — parity with
        # the previous switch.yutaki_control_demand_mode.
        HitachiYutakiSwitchEntityDescription(
            key="high_demand",
            name="High Demand",
            icon="mdi:water-plus",
            condition=lambda c: (
                c.has_dhw()
                and "dhw_high_demand" in c.api_client.register_map.all_registers
            ),
            get_fn=lambda api, _: api.get_dhw_high_demand(),
            set_fn=lambda api, _, enabled: api.set_dhw_high_demand(enabled),
        ),
    )

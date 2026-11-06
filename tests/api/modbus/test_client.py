"""Test ModbusApiClient unique_id retrieval."""

from __future__ import annotations

import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

from pymodbus.exceptions import ModbusException
import pytest

from custom_components.hitachi_yutaki.api.base import ReadResult
from custom_components.hitachi_yutaki.api.modbus import ModbusApiClient
from custom_components.hitachi_yutaki.api.modbus.registers import RegisterDefinition
from custom_components.hitachi_yutaki.api.modbus.registers.atw_mbs_02 import (
    AtwMbs02RegisterMap,
)
from custom_components.hitachi_yutaki.api.modbus.registers.atw_mbs_02_pre2016 import (
    AtwMbs02Pre2016RegisterMap,
)
from custom_components.hitachi_yutaki.api.modbus.registers.hc_a_mb import (
    HcAMbRegisterMap,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f: f())
    return hass


@pytest.fixture
def mock_client():
    """Create a mock Modbus client."""
    client = MagicMock()
    client.is_socket_open.return_value = True
    return client


@pytest.fixture
def api_client(mock_hass, mock_client):
    """Create a ModbusApiClient instance with mocked dependencies."""
    with patch.object(ModbusApiClient, "__init__", lambda x, *args, **kwargs: None):
        api = ModbusApiClient.__new__(ModbusApiClient)
        api._hass = mock_hass
        api._client = mock_client
        api._slave = 1
        api._register_map = AtwMbs02RegisterMap()
        api._pending_writes = {}
        return api


@pytest.mark.asyncio
async def test_async_get_unique_id_success(api_client, mock_client):
    """Test successful unique_id retrieval from input registers."""
    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = [3846, 103, 56]
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    assert result == "3846-103-56"
    mock_client.read_input_registers.assert_called_once()


@pytest.mark.asyncio
async def test_async_get_unique_id_different_values(api_client, mock_client):
    """Test unique_id with different register values."""
    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = [1234, 5678, 9012]
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    assert result == "1234-5678-9012"


@pytest.mark.asyncio
async def test_async_get_unique_id_modbus_error(api_client, mock_client):
    """Test unique_id retrieval when Modbus returns error."""
    mock_result = MagicMock()
    mock_result.isError.return_value = True
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    assert result is None


@pytest.mark.asyncio
async def test_async_get_unique_id_modbus_exception(api_client, mock_client):
    """Test unique_id retrieval when ModbusException is raised."""
    mock_client.read_input_registers.side_effect = ModbusException("Connection lost")

    result = await api_client.async_get_unique_id()

    assert result is None


@pytest.mark.asyncio
async def test_async_get_unique_id_connection_error(api_client, mock_client):
    """Test unique_id retrieval when ConnectionError occurs."""
    mock_client.read_input_registers.side_effect = ConnectionError(
        "Network unreachable"
    )

    result = await api_client.async_get_unique_id()

    assert result is None


@pytest.mark.asyncio
async def test_async_get_unique_id_os_error(api_client, mock_client):
    """Test unique_id retrieval when OSError occurs."""
    mock_client.read_input_registers.side_effect = OSError("Socket error")

    result = await api_client.async_get_unique_id()

    assert result is None


@pytest.mark.asyncio
async def test_async_get_unique_id_insufficient_registers(api_client, mock_client):
    """Test unique_id retrieval when fewer than 3 registers returned."""
    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = [3846, 103]  # Only 2 registers
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    assert result is None


@pytest.mark.asyncio
async def test_async_get_unique_id_zero_values(api_client, mock_client):
    """Test unique_id with zero register values."""
    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = [0, 0, 0]
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    # Zero values are still valid
    assert result == "0-0-0"


@pytest.mark.asyncio
async def test_async_get_unique_id_max_values(api_client, mock_client):
    """Test unique_id with maximum register values (16-bit)."""
    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = [65535, 65535, 65535]
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    assert result == "65535-65535-65535"


@pytest.mark.asyncio
async def test_async_get_unique_id_more_than_three_registers(api_client, mock_client):
    """Test unique_id when more than 3 registers returned (uses first 3)."""
    mock_result = MagicMock()
    mock_result.isError.return_value = False
    mock_result.registers = [3846, 103, 56, 999, 888]  # Extra registers
    mock_client.read_input_registers.return_value = mock_result

    result = await api_client.async_get_unique_id()

    # Should only use the first 3 registers
    assert result == "3846-103-56"


# --- Register fallback tests ---


def _make_modbus_result(value: int):
    """Create a mock Modbus result with a single register value."""
    result = MagicMock()
    result.isError.return_value = False
    result.registers = [value]
    return result


def _make_modbus_error():
    """Create a mock Modbus error result."""
    result = MagicMock()
    result.isError.return_value = True
    return result


def _make_modbus_result_list(values: list[int]):
    """Create a mock Modbus result carrying a block of register values."""
    result = MagicMock()
    result.isError.return_value = False
    result.registers = list(values)
    return result


class _FakeGateway:
    """Address-level fake of the heat pump gateway.

    The fork reads registers in blocks (FC04) plus a few holding singletons
    (FC03), so the transport can no longer be mocked by call order. This fake
    serves both function codes from one address -> raw value map, which lets a
    test state the intent ("register 1094 is 0") instead of the call sequence.

    Addresses that are not in the map read as 0. Addresses listed in
    ``errors`` answer with a Modbus error, which is how a failing block read
    is injected.
    """

    def __init__(
        self,
        values: dict[int, int] | None = None,
        errors: set[int] | None = None,
    ) -> None:
        """Store the register values and the addresses that fail."""
        self.values = dict(values or {})
        self.errors = set(errors or ())
        self.calls: list[tuple[str, int, int]] = []
        self.writes: list[tuple[int, int]] = []

    def _read(self, kind: str, address: int, count: int):
        """Answer a register read from the address map."""
        self.calls.append((kind, address, count))
        if any(a in self.errors for a in range(address, address + count)):
            return _make_modbus_error()
        return _make_modbus_result_list(
            [self.values.get(address + offset, 0) for offset in range(count)]
        )

    def read_input_registers(self, address, count=1, **kwargs):
        """Answer a block read (FC04)."""
        return self._read("fc04", address, count)

    def read_holding_registers(self, address, count=1, **kwargs):
        """Answer a holding register read (FC03)."""
        return self._read("fc03", address, count)

    def write_register(self, address, value, **kwargs):
        """Accept a register write (FC06)."""
        self.writes.append((address, value))
        return _make_modbus_result(0)

    def is_socket_open(self):
        """Report an open socket."""
        return True

    def close(self):
        """Close the (fake) connection."""
        return True

    def block_reads(self) -> list[tuple[int, int]]:
        """Return the (address, count) of every block read (FC04)."""
        return [
            (address, count) for kind, address, count in self.calls if kind == "fc04"
        ]


@pytest.mark.asyncio
async def test_read_input_block_returns_raw_values(api_client, mock_client):
    """A block read returns the raw register list of the requested window."""
    mock_client.read_input_registers.return_value = _make_modbus_result_list(
        [10, 20, 30]
    )

    values = await api_client._read_input_block(1050, 3, "slave")

    assert values == [10, 20, 30]
    kwargs = mock_client.read_input_registers.call_args.kwargs
    assert kwargs["address"] == 1050
    assert kwargs["count"] == 3


@pytest.mark.asyncio
async def test_read_input_block_returns_none_on_error(api_client, mock_client):
    """A Modbus error on a block read yields None, not an exception."""
    mock_client.read_input_registers.return_value = _make_modbus_error()

    assert await api_client._read_input_block(1050, 3, "slave") is None


@pytest.mark.asyncio
async def test_read_holding_one_returns_value(api_client, mock_client):
    """A holding singleton is read one register at a time (FC03)."""
    mock_client.read_holding_registers.return_value = _make_modbus_result(42)

    assert await api_client._read_holding_one(1010, "slave") == 42
    kwargs = mock_client.read_holding_registers.call_args.kwargs
    assert kwargs["address"] == 1010
    assert kwargs["count"] == 1


@pytest.mark.asyncio
async def test_read_holding_one_returns_none_on_error(api_client, mock_client):
    """A Modbus error on a holding singleton yields None."""
    mock_client.read_holding_registers.return_value = _make_modbus_error()

    assert await api_client._read_holding_one(1010, "slave") is None


def test_decode_register_deserializes_value(api_client):
    """The deserializer of the definition converts the raw register value."""
    definition = RegisterDefinition(1200, deserializer=lambda v: v / 10.0)

    assert api_client._decode_register(definition, 350) == 35.0


def test_decode_register_returns_raw_value_without_deserializer(api_client):
    """Without a deserializer the raw register value is returned as is."""
    definition = RegisterDefinition(1000)

    assert api_client._decode_register(definition, 42) == 42


def test_decode_register_returns_none_for_missing_value(api_client):
    """A failed read (no raw value at all) decodes to None."""
    definition = RegisterDefinition(1200)

    assert api_client._decode_register(definition, None) is None


def test_decode_register_filters_sentinel_value(api_client):
    """A gateway sentinel is reported as filtered, not as a value."""
    definition = RegisterDefinition(1089, sentinel_values=frozenset({0xFFFF}))

    assert (
        api_client._decode_register(definition, 0xFFFF) is api_client._SENTINEL_FILTERED
    )


# --- Block planning (fork-specific) ---


def test_plan_input_blocks_merges_near_addresses(api_client):
    """Addresses within the merge gap become a single block."""
    assert api_client._plan_input_blocks({1091, 1092, 1094}) == [(1091, 4)]


def test_plan_input_blocks_splits_on_large_gap(api_client):
    """A gap wider than the merge limit starts a new block."""
    assert api_client._plan_input_blocks({1094, 1200}) == [(1094, 1), (1200, 1)]


def test_plan_input_blocks_skips_addresses_outside_proven_ranges(api_client):
    """Only addresses proven for FC04 are planned as input blocks."""
    assert api_client._plan_input_blocks({1010, 1021, 1094}) == [(1094, 1)]


def test_plan_input_blocks_respects_max_block_count(api_client):
    """A block never exceeds the Modbus-safe register count."""
    api_client._register_map = _WideRangeMap()
    addresses = set(range(1050, 1050 + 70))

    blocks = api_client._plan_input_blocks(addresses)

    assert blocks == [(1050, 64), (1114, 6)]
    assert all(count <= api_client._MAX_BLOCK_COUNT for _, count in blocks)


class _WideRangeMap:
    """Register map stub declaring a wide proven FC04 range."""

    input_read_ranges = ((1050, 1200),)


# --- Fallback register handling ---


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_fallback_used_when_primary_returns_none(
    _mock_ir, mock_hass, mock_client
):
    """A sensor-error primary (0xFFFF) falls back to the fallback register."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0, 1200: 0xFFFF, 1093: 350})

    result = await api.read_values(["water_outlet_temp"])

    assert result == ReadResult.SUCCESS
    assert api._data["water_outlet_temp"] == 350


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_fallback_not_used_when_primary_succeeds(
    _mock_ir, mock_hass, mock_client
):
    """A valid primary wins over the fallback register."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0, 1200: 280, 1093: 350})

    result = await api.read_values(["water_outlet_temp"])

    assert result == ReadResult.SUCCESS
    assert api._data["water_outlet_temp"] == 280


def test_fallback_used_when_primary_read_errors(api_client):
    """A failed primary read yields to the fallback register."""
    definition = RegisterDefinition(
        1200,
        fallback=RegisterDefinition(1093),
    )

    value = api_client._decode_register(definition, None)
    if value is None and definition.fallback:
        value = api_client._decode_register(definition.fallback, 280)

    assert value == 280


def test_fallback_also_fails_returns_none(api_client):
    """None is returned when both primary and fallback have no value."""
    definition = RegisterDefinition(
        1200,
        fallback=RegisterDefinition(1093),
    )

    value = api_client._decode_register(definition, None)
    if value is None and definition.fallback:
        value = api_client._decode_register(definition.fallback, None)

    assert value is None


# --- Preflight / system_state deserialization tests ---


def _make_preflight_api_client(mock_hass, mock_client):
    """Create a ModbusApiClient with register map for preflight tests."""
    with patch.object(ModbusApiClient, "__init__", lambda x, *args, **kwargs: None):
        api = ModbusApiClient.__new__(ModbusApiClient)
        api._hass = mock_hass
        api._client = mock_client
        api._slave = 1
        api._data = {}
        api._register_map = AtwMbs02RegisterMap()
        api._gateway_not_ready_since = None
        api._gateway_not_ready_last_log = 0.0
        api._pending_writes = {}
        return api


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_deserializes_system_state_on_state_0(
    mock_ir, mock_hass, mock_client
):
    """Test system_state is deserialized to 'synchronized' when state is 0."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0})

    result = await api.read_values(["system_state"])

    assert result == ReadResult.SUCCESS
    assert api._data["system_state"] == "synchronized"


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_deserializes_system_state_on_state_2(
    mock_ir, mock_hass, mock_client
):
    """Test system_state is deserialized to 'initializing' when state is 2."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 2})

    result = await api.read_values(["system_state"])

    assert result == ReadResult.GATEWAY_NOT_READY
    assert api._data["system_state"] == "initializing"


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_deserializes_system_state_on_state_1(
    mock_ir, mock_hass, mock_client
):
    """Test system_state is deserialized to 'desynchronized' when state is 1."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 1})

    result = await api.read_values(["system_state"])

    assert result == ReadResult.GATEWAY_NOT_READY
    assert api._data["system_state"] == "desynchronized"


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_returns_success_on_normal_read(
    mock_ir, mock_hass, mock_client
):
    """Test read_values returns SUCCESS when gateway is synchronized."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0})

    result = await api.read_values(["system_state"])

    assert result == ReadResult.SUCCESS


@pytest.mark.asyncio
@patch("custom_components.hitachi_yutaki.api.modbus.ir")
async def test_read_values_throttles_gateway_not_ready_logs(
    _mock_ir, mock_hass, mock_client, caplog
):
    """Test that repeated gateway-not-ready warnings are throttled."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 2})

    # First call should log
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        await api.read_values(["system_state"])
        first_warnings = [r for r in caplog.records if "not ready" in r.message]
        assert len(first_warnings) == 1

    # Second call immediately after should NOT log
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        await api.read_values(["system_state"])
        second_warnings = [r for r in caplog.records if "not ready" in r.message]
        assert len(second_warnings) == 0


@pytest.mark.asyncio
@patch("custom_components.hitachi_yutaki.api.modbus.ir")
async def test_read_values_resets_throttle_state_on_recovery(
    _mock_ir, mock_hass, mock_client, caplog
):
    """Test that throttle state is reset and a recovery line is logged (#356)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    gateway = _FakeGateway({1094: 2})
    api._client = gateway

    # Not ready
    await api.read_values(["system_state"])
    assert api._gateway_not_ready_since is not None

    # Recovered
    gateway.values[1094] = 0
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        await api.read_values(["system_state"])
    assert api._gateway_not_ready_since is None
    assert api._gateway_not_ready_last_log == 0.0
    recovery_logs = [r for r in caplog.records if "recovered" in r.message.lower()]
    assert len(recovery_logs) == 1


# --- Stale-value clearing on sensor-error / read-error (issue #320) ---


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_clears_stale_value_on_sensor_error_without_fallback(
    _mock_ir, mock_hass, mock_client
):
    """A 0xFFFF sensor-error with no fallback must clear the stale value (#320)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["outdoor_temp"] = 5  # stale good value
    api._client = _FakeGateway({1094: 0, 1091: 0xFFFF})

    result = await api.read_values(["outdoor_temp"])

    assert result == ReadResult.SUCCESS
    assert "outdoor_temp" not in api._data


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_clears_stale_value_on_read_error_without_fallback(
    _mock_ir, mock_hass, mock_client
):
    """A read error outside the block ranges clears just that entity (#320).

    Addresses outside the proven FC04 ranges are read one by one (FC03), so a
    failing read stays local to its entity, exactly as upstream does.
    """
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["circuit1_thermostat"] = 21  # stale good value
    api._client = _FakeGateway({1094: 0}, errors={1010})

    result = await api.read_values(["circuit1_thermostat"])

    assert result == ReadResult.SUCCESS
    assert "circuit1_thermostat" not in api._data


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_block_error_aborts_cycle(_mock_ir, mock_hass, mock_client):
    """A failing block read aborts the cycle instead of reporting partial data.

    The block ranges are read as one transaction, so a failed block cannot be
    attributed to a single register: the cycle fails and is retried after a
    reconnect, instead of publishing half-updated values.
    """
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0}, errors={1091})
    api._ensure_connection = AsyncMock(return_value=False)

    with pytest.raises(ModbusException):
        await api.read_values(["outdoor_temp"])

    assert "outdoor_temp" not in api._data


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_keeps_value_on_successful_read(
    _mock_ir, mock_hass, mock_client
):
    """A fresh successful read overwrites the stored value (regression guard)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["outdoor_temp"] = 5  # stale value to be overwritten
    api._client = _FakeGateway({1094: 0, 1091: 200})  # convert_signed_16bit(200) == 200

    result = await api.read_values(["outdoor_temp"])

    assert result == ReadResult.SUCCESS
    assert api._data["outdoor_temp"] == 200


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_fallback_still_recovers_on_sensor_error(
    _mock_ir, mock_hass, mock_client
):
    """Fallback register must still recover when primary is a 0xFFFF sensor-error."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0, 1200: 0xFFFF, 1093: 350})

    result = await api.read_values(["water_outlet_temp"])

    assert result == ReadResult.SUCCESS
    assert api._data["water_outlet_temp"] == 350


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_clears_when_both_primary_and_fallback_error(
    _mock_ir, mock_hass, mock_client
):
    """When both primary and fallback error, the stale value must be cleared (#320)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["water_outlet_temp"] = 42  # stale good value
    api._client = _FakeGateway({1094: 0, 1200: 0xFFFF, 1093: 0xFFFF})

    result = await api.read_values(["water_outlet_temp"])

    assert result == ReadResult.SUCCESS
    assert "water_outlet_temp" not in api._data


@pytest.mark.asyncio
@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@patch("custom_components.hitachi_yutaki.api.modbus.time")
async def test_read_values_logs_periodic_reminder_after_5_minutes(
    mock_time, _mock_ir, mock_hass, mock_client, caplog
):
    """Test that a periodic reminder is logged after 5 minutes of gateway-not-ready."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 2})

    # First call at t=0
    mock_time.monotonic.return_value = 1000.0
    await api.read_values(["system_state"])

    # Second call at t=100s - should NOT log
    mock_time.monotonic.return_value = 1100.0
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        await api.read_values(["system_state"])
        warnings = [
            r
            for r in caplog.records
            if "not ready" in r.message.lower()
            or "still not ready" in r.message.lower()
        ]
        assert len(warnings) == 0

    # Third call at t=301s - SHOULD log periodic reminder
    mock_time.monotonic.return_value = 1301.0
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        await api.read_values(["system_state"])
        reminders = [
            r for r in caplog.records if "still not ready" in r.message.lower()
        ]
        assert len(reminders) == 1
        assert "5 minutes" in reminders[0].message


def test_get_operation_state_reads_data():
    """get_operation_state returns the deserialized operation_state from _data."""
    with patch.object(ModbusApiClient, "__init__", lambda x, *args, **kwargs: None):
        api = ModbusApiClient.__new__(ModbusApiClient)
        api._data = {"operation_state": "operation_state_heat_thermo_on"}
        assert api.get_operation_state() == "operation_state_heat_thermo_on"


def test_get_operation_state_absent_returns_none():
    """get_operation_state returns None when operation_state is absent."""
    with patch.object(ModbusApiClient, "__init__", lambda x, *args, **kwargs: None):
        api = ModbusApiClient.__new__(ModbusApiClient)
        api._data = {}
        assert api.get_operation_state() is None


@pytest.fixture
def pre2016_api_client(mock_hass, mock_client):
    """Create a ModbusApiClient wired with the pre-2016 register map for write tests."""
    with patch.object(ModbusApiClient, "__init__", lambda x, *args, **kwargs: None):
        api = ModbusApiClient.__new__(ModbusApiClient)
        api._hass = mock_hass
        api._client = mock_client
        api._slave = 1
        api._register_map = AtwMbs02Pre2016RegisterMap()
        api._data = {}
        api._pending_writes = {}
        write_result = MagicMock()
        write_result.isError.return_value = False
        mock_client.write_register.return_value = write_result
        return api


class TestGlobalEcoAccessors:
    """Behavior of the global (pre-2016) eco accessors.

    The pre-2016 Space mode register is NON-inverted (0=Comfort, 1=ECO),
    unlike the 2016+ per-circuit eco registers which are inverted
    (0=eco, 1=comfort). These tests lock that convention in.
    """

    def test_get_eco_mode_non_inverted(self, pre2016_api_client):
        """Raw 1 means ECO on, raw 0 means Comfort (off), absent means None."""
        pre2016_api_client._data = {"eco_mode": 1}
        assert pre2016_api_client.get_eco_mode() is True
        pre2016_api_client._data = {"eco_mode": 0}
        assert pre2016_api_client.get_eco_mode() is False
        pre2016_api_client._data = {}
        assert pre2016_api_client.get_eco_mode() is None

    @pytest.mark.asyncio
    async def test_set_eco_mode_writes_raw_1_at_1027(
        self, pre2016_api_client, mock_client
    ):
        """Enabling ECO writes raw 1 (non-inverted) to address 1027."""
        assert await pre2016_api_client.set_eco_mode(True) is True
        kwargs = mock_client.write_register.call_args.kwargs
        assert kwargs["address"] == 1027
        assert kwargs["value"] == 1

    @pytest.mark.asyncio
    async def test_set_eco_mode_writes_raw_0_when_disabled(
        self, pre2016_api_client, mock_client
    ):
        """Disabling ECO writes raw 0 (Comfort) to address 1027."""
        assert await pre2016_api_client.set_eco_mode(False) is True
        kwargs = mock_client.write_register.call_args.kwargs
        assert kwargs["address"] == 1027
        assert kwargs["value"] == 0

    def test_get_eco_offset_reads_data(self, pre2016_api_client):
        """get_eco_offset returns the raw buffered value, None when absent."""
        pre2016_api_client._data = {"eco_offset": 4}
        assert pre2016_api_client.get_eco_offset() == 4
        pre2016_api_client._data = {}
        assert pre2016_api_client.get_eco_offset() is None

    @pytest.mark.asyncio
    async def test_set_eco_offset_writes_control_address_1030(
        self, pre2016_api_client, mock_client
    ):
        """A valid offset is written to CONTROL 1030, not STATUS 1090."""
        assert await pre2016_api_client.set_eco_offset(5) is True
        kwargs = mock_client.write_register.call_args.kwargs
        assert kwargs["address"] == 1030
        assert kwargs["value"] == 5

    @pytest.mark.asyncio
    @pytest.mark.parametrize("offset", [0, 11])
    async def test_set_eco_offset_rejects_out_of_range_without_write(
        self, pre2016_api_client, mock_client, offset
    ):
        """Out-of-range offsets are rejected before any Modbus write."""
        assert await pre2016_api_client.set_eco_offset(offset) is False
        mock_client.write_register.assert_not_called()


# --- Garbage system_config read (issue #404) ---


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_filters_garbage_system_config(
    _mock_ir, mock_hass, mock_client
):
    """A 0xFFFF system_config is filtered, not decoded as every capability (#404)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["system_config"] = 0x0021  # stale good value
    api._client = _FakeGateway({1094: 0, 1089: 0xFFFF})

    result = await api.read_values(["system_config"])

    assert result == ReadResult.SUCCESS
    assert "system_config" not in api._data
    assert api.has_dhw is False
    assert api.has_pool is False


@pytest.mark.parametrize(
    "register_map",
    [AtwMbs02RegisterMap(), AtwMbs02Pre2016RegisterMap(), HcAMbRegisterMap()],
    ids=["atw_mbs_02", "atw_mbs_02_pre2016", "hc_a_mb"],
)
def test_system_config_declares_garbage_sentinel(register_map):
    """Every register map filters a 0xFFFF system_config (#404)."""
    sentinels = register_map.all_registers["system_config"].sentinel_values
    assert sentinels is not None
    assert 0xFFFF in sentinels


@pytest.mark.parametrize(
    "register_map",
    [AtwMbs02RegisterMap(), AtwMbs02Pre2016RegisterMap(), HcAMbRegisterMap()],
    ids=["atw_mbs_02", "atw_mbs_02_pre2016", "hc_a_mb"],
)
@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_system_state_ffff_is_not_ready(
    mock_ir, mock_hass, mock_client, register_map
):
    """A 0xFFFF system_state (no heat pump data) is not ready, not healthy (#404)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._register_map = register_map
    system_state_addr = register_map.all_registers["system_state"].address
    gateway = _FakeGateway({system_state_addr: 0xFFFF})
    api._client = gateway

    result = await api.read_values(["system_config"])

    assert result == ReadResult.GATEWAY_NOT_READY
    assert "system_config" not in api._data
    # The preflight read is the only transaction of this cycle.
    assert len(gateway.calls) == 1
    mock_ir.async_create_issue.assert_called_once()
    assert mock_ir.async_create_issue.call_args.args[2] == "no_data_warning"


# --- Pending writes: a command must not show up, revert, then show up again ---


@pytest.mark.asyncio
async def test_write_value_publishes_expected_value_at_once(mock_hass, mock_client):
    """A successful write is visible in ``_data`` before any poll, deserialized."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["circuit1_target_temp"] = 21.0
    mock_client.write_register.return_value = _make_modbus_result(0)

    assert await api.write_value("circuit1_target_temp", 225) is True

    assert api._data["circuit1_target_temp"] == 22.5
    assert api._pending_writes["circuit1_target_temp"][0] == 22.5
    assert mock_client.write_register.call_args.kwargs["address"] == 1011


@pytest.mark.asyncio
async def test_failed_write_shadows_nothing(mock_hass, mock_client):
    """A refused write leaves both the data and the pending map untouched (#322)."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._data["unit_power"] = 0
    mock_client.write_register.return_value = _make_modbus_error()
    api._ensure_connection = AsyncMock(return_value=False)

    assert await api.write_value("unit_power", 1) is False

    assert api._data["unit_power"] == 0
    assert api._pending_writes == {}


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_ignores_stale_status_after_write(
    _mock_ir, mock_hass, mock_client
):
    """Polls still reporting the pre-write value do not revert the entity."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    gateway = _FakeGateway({1094: 0, 1050: 0})
    api._client = gateway
    await api.write_value("unit_power", 1)

    # The gateway still reports the pre-write value.
    assert await api.read_values(["unit_power"]) == ReadResult.SUCCESS
    assert api._data["unit_power"] == 1

    # A read error in the window keeps the expected value too (not #320's clear).
    gateway.errors.add(1050)
    api._ensure_connection = AsyncMock(return_value=False)
    with pytest.raises(ModbusException):
        await api.read_values(["unit_power"])
    assert api._data["unit_power"] == 1
    assert "unit_power" in api._pending_writes


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_confirms_write_and_lifts_shadow(
    _mock_ir, mock_hass, mock_client
):
    """A STATUS read equal to the written value ends the shadow."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    gateway = _FakeGateway({1094: 0, 1050: 1})
    api._client = gateway
    await api.write_value("unit_power", 1)

    await api.read_values(["unit_power"])
    assert api._pending_writes == {}

    # From then on the gateway is the truth again (e.g. the unit turned off).
    gateway.values[1050] = 0
    await api.read_values(["unit_power"])
    assert api._data["unit_power"] == 0


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_read_values_accepts_gateway_value_after_ttl(
    _mock_ir, mock_hass, mock_client
):
    """Past the deadline an unconfirmed write yields to the gateway value."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0, 1050: 0})
    await api.write_value("unit_power", 1)
    api._pending_writes["unit_power"] = (1, time.monotonic() - 1)

    await api.read_values(["unit_power"])

    assert api._data["unit_power"] == 0
    assert api._pending_writes == {}


@patch("custom_components.hitachi_yutaki.api.modbus.ir")
@pytest.mark.asyncio
async def test_successive_writes_last_value_wins_and_rearms_deadline(
    _mock_ir, mock_hass, mock_client
):
    """On -> off on one key: the last expected value, with a later deadline."""
    api = _make_preflight_api_client(mock_hass, mock_client)
    api._client = _FakeGateway({1094: 0, 1050: 1})
    await api.write_value("unit_power", 1)
    expected, deadline = api._pending_writes["unit_power"]
    earlier = deadline - 5
    api._pending_writes["unit_power"] = (expected, earlier)

    await api.write_value("unit_power", 0)

    expected, deadline = api._pending_writes["unit_power"]
    assert (expected, api._data["unit_power"]) == (0, 0)
    assert deadline > earlier

    # The first write's value is stale now, not a confirmation.
    await api.read_values(["unit_power"])
    assert api._data["unit_power"] == 0
    assert "unit_power" in api._pending_writes

import base64
import contextlib
import logging
from typing import TYPE_CHECKING

from homeassistant.components import infrared
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_OFF,
    SWING_VERTICAL,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
from infrared_protocols.commands import hitachi

from .const import (
    CONF_COOL_ONLY,
    CONF_EMITTER_ENTITY_ID,
    CONF_HUMIDITY_SENSOR,
    CONF_PROTOCOL,
    CONF_TEMPERATURE_SENSOR,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None) -> None:
    """Set up the Hitachi Infrared Remote climate platform from YAML."""
    name = config.get("name")
    remote_entity = config.get("remote_entity")
    temp_sensor = config.get(
        "temperature_sensor"
    )  # External temperature sensor entity ID
    humidity_sensor = config.get(
        "humidity_sensor"
    )  # External humidity sensor entity ID
    encoding = config.get("encoding", "broadlink")  # broadlink, pronto, raw
    unique_id = config.get("unique_id")
    protocol = config.get("protocol", "ac344")
    cool_only = config.get(
        "cool_only", False
    )  # Cool-only AC flag (default False for Heat/Cool)
    add_entities(
        [
            HitachiIRClimate(
                hass,
                name,
                remote_entity,
                temp_sensor,
                humidity_sensor,
                encoding,
                unique_id,
                protocol,
                cool_only,
            )
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hitachi Infrared Remote climate platform from a config entry."""

    config = config_entry.data
    name = config.get("name")
    remote_entity = config.get(CONF_EMITTER_ENTITY_ID)
    temp_sensor = config.get(CONF_TEMPERATURE_SENSOR)
    humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
    protocol = config.get(CONF_PROTOCOL, "ac344")
    cool_only = config.get(CONF_COOL_ONLY, False)
    encoding = config.get("encoding", "broadlink")
    unique_id = config_entry.unique_id or config_entry.entry_id

    async_add_entities(
        [
            HitachiIRClimate(
                hass=hass,
                name=name,
                remote_entity=remote_entity,
                temp_sensor=temp_sensor,
                humidity_sensor=humidity_sensor,
                encoding=encoding,
                unique_id=unique_id,
                protocol=protocol,
                cool_only=cool_only,
            )
        ]
    )


class HitachiIRClimate(ClimateEntity):
    """Representation of a Hitachi Infrared Climate entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass,
        name=None,
        remote_entity=None,
        temp_sensor=None,
        humidity_sensor=None,
        encoding="broadlink",
        unique_id=None,
        protocol="ac344",
        cool_only=False,
    ) -> None:
        """Initialize the Hitachi IR Climate entity."""
        self.hass = hass
        self._attr_name = name
        self._remote_entity = remote_entity
        self._temp_sensor = temp_sensor
        self._humidity_sensor = humidity_sensor
        self._encoding = encoding
        self._protocol = protocol
        self._cool_only = cool_only

        if unique_id:
            self._attr_unique_id = unique_id
        elif name:
            try:
                from homeassistant.util import slugify

                clean_name = slugify(name)
            except ImportError:
                clean_name = name.lower().replace(" ", "_")
            self._attr_unique_id = f"climate_{clean_name}"
        elif remote_entity:
            clean_remote = remote_entity.replace(".", "_")
            self._attr_unique_id = f"climate_{clean_remote}"

        self._attr_current_temperature = None
        self._attr_current_humidity = None
        self._last_button = hitachi.HitachiAcButton.POWER

        # Sync temperature limits from protocol definition
        self._attr_min_temp = hitachi.MIN_TEMP
        self._attr_max_temp = hitachi.MAX_TEMP
        self._attr_temperature_unit = "°C"
        self._attr_target_temperature_step = 1

        # Supported HVAC modes (add HEAT mode if not cool-only)
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.AUTO,
        ]
        if not self._cool_only:
            self._attr_hvac_modes.append(HVACMode.HEAT)

        # Supported vertical swing modes
        self._attr_swing_modes = [SWING_OFF, SWING_VERTICAL]

        # Supported horizontal swing modes (deduplicated 7 steps into 6 states)
        self._attr_swing_horizontal_modes = [
            "auto",
            "right_max",
            "right",
            "middle",
            "left",
            "left_max",
        ]

        # Initial state defaults
        self._attr_hvac_mode = HVACMode.COOL
        self._attr_target_temperature = 26
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        self._attr_swing_horizontal_mode = "middle"

        # Advanced feature states (timers, mold prevention)
        self._on_timer_mins = None
        self._off_timer_mins = None
        self._mold_prevention = False
        self._mold_duration = hitachi.HitachiAcMoldDuration.MINS_30

        # Initialize dynamic attributes and feature flags
        self._update_supported_limits()

    def _update_supported_limits(self) -> None:
        """Dynamically update supported features and fan modes based on current HVAC mode."""
        mode = self._attr_hvac_mode

        if mode == HVACMode.FAN_ONLY:
            # Target temperature is not supported in FAN_ONLY mode
            self._attr_supported_features = (
                ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )
            # FAN_ONLY mode fan speeds (excludes AUTO)
            self._attr_fan_modes = [FAN_HIGH, FAN_MEDIUM, FAN_LOW, "silent"]
            self._attr_target_temperature = None
            if self._attr_fan_mode not in self._attr_fan_modes:
                self._attr_fan_mode = FAN_HIGH

        elif mode == HVACMode.AUTO:
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )
            # AUTO mode fan speeds
            self._attr_fan_modes = [FAN_AUTO, FAN_LOW, "silent"]
            if self._attr_target_temperature is None:
                self._attr_target_temperature = 25  # Default reference temperature
            if self._attr_fan_mode not in self._attr_fan_modes:
                self._attr_fan_mode = FAN_AUTO

        elif mode == HVACMode.DRY:
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )
            # DRY mode fan speeds
            self._attr_fan_modes = [FAN_LOW, "silent"]
            if self._attr_target_temperature is None:
                self._attr_target_temperature = 26
            if self._attr_fan_mode not in self._attr_fan_modes:
                self._attr_fan_mode = FAN_LOW

        else:  # COOL, HEAT, OFF
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )
            self._attr_fan_modes = [
                FAN_AUTO,
                FAN_HIGH,
                FAN_MEDIUM,
                FAN_LOW,
                "silent",
            ]
            if self._attr_target_temperature is None:
                self._attr_target_temperature = 26
            if self._attr_fan_mode not in self._attr_fan_modes:
                self._attr_fan_mode = FAN_AUTO

    async def async_added_to_hass(self) -> None:
        """Set up external temperature and humidity sensor state change listeners when entity is added."""
        await super().async_added_to_hass()

        if self._temp_sensor:
            # Fetch initial state
            state = self.hass.states.get(self._temp_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                with contextlib.suppress(ValueError):
                    self._attr_current_temperature = float(state.state)

            # Listen for state changes
            @callback
            def _async_temp_sensor_changed(event) -> None:
                new_state = event.data.get("new_state")
                if new_state and new_state.state not in ["unknown", "unavailable"]:
                    with contextlib.suppress(ValueError):
                        self._attr_current_temperature = float(new_state.state)
                        self.async_write_ha_state()

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._temp_sensor], _async_temp_sensor_changed
                )
            )

        if self._humidity_sensor:
            # Fetch initial state
            state = self.hass.states.get(self._humidity_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                with contextlib.suppress(ValueError):
                    self._attr_current_humidity = float(state.state)

            # Listen for state changes
            @callback
            def _async_humidity_sensor_changed(event) -> None:
                new_state = event.data.get("new_state")
                if new_state and new_state.state not in ["unknown", "unavailable"]:
                    with contextlib.suppress(ValueError):
                        self._attr_current_humidity = float(new_state.state)
                        self.async_write_ha_state()

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._humidity_sensor], _async_humidity_sensor_changed
                )
            )

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            self._attr_target_temperature = int(kwargs[ATTR_TEMPERATURE])
            self._last_button = hitachi.HitachiAcButton.TEMPERATURE
            await self.async_send_ir_command()

    async def async_set_hvac_mode(self, hvac_mode) -> None:
        """Set HVAC mode."""
        if self._cool_only and hvac_mode == HVACMode.HEAT:
            _LOGGER.error("Cool-only AC does not support HEAT mode")
            return
        old_mode = self._attr_hvac_mode
        self._attr_hvac_mode = hvac_mode
        self._update_supported_limits()

        if HVACMode.OFF in (hvac_mode, old_mode):
            self._last_button = hitachi.HitachiAcButton.POWER
        else:
            self._last_button = hitachi.HitachiAcButton.MODE

        await self.async_send_ir_command()

    async def async_set_fan_mode(self, fan_mode) -> None:
        """Set fan mode."""
        self._attr_fan_mode = fan_mode
        self._last_button = hitachi.HitachiAcButton.FAN
        await self.async_send_ir_command()

    async def async_set_swing_mode(self, swing_mode) -> None:
        """Set vertical swing mode."""
        self._attr_swing_mode = swing_mode
        self._last_button = hitachi.HitachiAcButton.SWING_V
        await self.async_send_ir_command()

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode) -> None:
        """Set horizontal swing mode."""
        self._attr_swing_horizontal_mode = swing_horizontal_mode
        self._last_button = hitachi.HitachiAcButton.SWING_H
        await self.async_send_ir_command()

    async def async_set_timer(self, minutes: int) -> None:
        """Set timer schedule (OFF timer when ON, ON timer when OFF)."""
        if self._attr_hvac_mode == HVACMode.OFF:
            # When OFF: schedule ON timer
            self._on_timer_mins = minutes
            self._off_timer_mins = None
        else:
            # When ON: schedule OFF timer
            self._off_timer_mins = minutes
            self._on_timer_mins = None

        self._last_button = hitachi.HitachiAcButton.OFF_TIMER
        await self.async_send_ir_command()

    async def async_cancel_timer(self) -> None:
        """Cancel active timer schedule."""
        self._on_timer_mins = None
        self._off_timer_mins = None
        self._last_button = hitachi.HitachiAcButton.CANCEL_TIMER
        await self.async_send_ir_command()

    async def async_run_clean(self) -> None:
        """Run clean cycle (allowed only in OFF state)."""
        if self._attr_hvac_mode != HVACMode.OFF:
            _LOGGER.error("Clean cycle can only be executed when HVAC is OFF")
            return
        self._last_button = hitachi.HitachiAcButton.CLEAN
        await self.async_send_ir_command()

    async def async_set_mold_prevention(self, active: bool, duration: int = 30) -> None:
        """Set mold prevention feature and duration (COOL/DRY modes only)."""
        if self._attr_hvac_mode not in [HVACMode.COOL, HVACMode.DRY]:
            _LOGGER.error("Mold prevention can only be enabled in COOL or DRY mode")
            return

        self._mold_prevention = active
        duration_mapping = {
            10: hitachi.HitachiAcMoldDuration.MINS_10,
            20: hitachi.HitachiAcMoldDuration.MINS_20,
            30: hitachi.HitachiAcMoldDuration.MINS_30,
            45: hitachi.HitachiAcMoldDuration.MINS_45,
            60: hitachi.HitachiAcMoldDuration.MINS_60,
        }
        self._mold_duration = duration_mapping.get(
            duration, hitachi.HitachiAcMoldDuration.MINS_30
        )
        self._last_button = hitachi.HitachiAcButton.MOLD
        await self.async_send_ir_command()

    async def async_send_ir_command(self) -> None:
        """Translate HA state to Hitachi protocol command and transmit."""
        is_on = self._attr_hvac_mode != HVACMode.OFF

        # HVAC mode mapping
        mode_mapping = {
            HVACMode.COOL: hitachi.HitachiAcMode.COOL,
            HVACMode.DRY: hitachi.HitachiAcMode.DRY,
            HVACMode.HEAT: hitachi.HitachiAcMode.HEAT,
            HVACMode.FAN_ONLY: hitachi.HitachiAcMode.FAN_ONLY,
            HVACMode.AUTO: hitachi.HitachiAcMode.AUTO,
            HVACMode.OFF: hitachi.HitachiAcMode.COOL,
        }
        current_mode = mode_mapping.get(
            self._attr_hvac_mode, hitachi.HitachiAcMode.COOL
        )

        # Fan speed mapping
        fan_mapping = {
            FAN_AUTO: hitachi.HitachiAcFanSpeed.AUTO,
            FAN_HIGH: hitachi.HitachiAcFanSpeed.HIGH,
            FAN_MEDIUM: hitachi.HitachiAcFanSpeed.MEDIUM,
            FAN_LOW: hitachi.HitachiAcFanSpeed.LOW,
            "silent": hitachi.HitachiAcFanSpeed.SILENT,
        }
        current_fan = fan_mapping.get(
            self._attr_fan_mode, hitachi.HitachiAcFanSpeed.AUTO
        )

        # Temperature mapping
        if current_mode == hitachi.HitachiAcMode.AUTO:
            # AUTO mode: calculate offset relative to current ambient temperature
            base_temp = (
                self._attr_current_temperature
                if self._attr_current_temperature is not None
                else 25
            )
            temp_offset = round(self._attr_target_temperature - base_temp)
            target_temp = max(-3, min(3, temp_offset))
        elif current_mode == hitachi.HitachiAcMode.FAN_ONLY:
            # FAN_ONLY mode does not transmit target temperature (filler 27°C used for payload structure)
            target_temp = 27
        else:
            target_temp = self._attr_target_temperature

        # Swing and horizontal swing state
        is_swing_v = self._attr_swing_mode == SWING_VERTICAL
        h_mapping = {
            "auto": hitachi.HitachiAcSwingH.AUTO,
            "right_max": hitachi.HitachiAcSwingH.RIGHT_MAX,
            "right": hitachi.HitachiAcSwingH.RIGHT,
            "middle": hitachi.HitachiAcSwingH.MIDDLE,
            "left": hitachi.HitachiAcSwingH.LEFT,
            "left_max": hitachi.HitachiAcSwingH.LEFT_MAX,
        }
        current_swing_h = h_mapping.get(
            self._attr_swing_horizontal_mode, hitachi.HitachiAcSwingH.MIDDLE
        )

        # Determine button code to transmit
        button_code = hitachi.HitachiAcButton.POWER if not is_on else self._last_button

        _LOGGER.warning(
            "Sending command: mode %s, temp %s, fan %s, swing_v %s, swing_h %s, button %s",
            self._attr_hvac_mode,
            target_temp,
            self._attr_fan_mode,
            self._attr_swing_mode,
            self._attr_swing_horizontal_mode,
            button_code.name,
        )

        # Instantiate command object based on configured protocol
        protocol_map = {
            "ac344": hitachi.HitachiAc344Command,
        }
        command_class = protocol_map.get(self._protocol, hitachi.HitachiAc344Command)
        command = command_class(
            temperature=target_temp,
            mode=current_mode,
            fan=current_fan,
            power=is_on,
            swing_v=is_swing_v,
            swing_h=current_swing_h,
            off_timer_mins=self._off_timer_mins,
            on_timer_mins=self._on_timer_mins,
            mold_prevention=self._mold_prevention,
            mold_duration=self._mold_duration,
            button=button_code,
        )

        # For HA infrared entity, send command object via async_send_command
        if self._remote_entity.startswith("infrared."):
            await infrared.async_send_command(
                self.hass, self._remote_entity, command, context=self._context
            )
            return

        # For traditional remote entity, get raw timings and encode payload
        raw_timings = command.get_raw_timings()

        if self._encoding == "broadlink":
            # Broadlink Base64 encoding
            pulses = []
            for t in raw_timings:
                val = round(abs(t) / 26.9)
                if val > 255:
                    pulses.extend([0x00, (val >> 8) & 0xFF, val & 0xFF])
                else:
                    pulses.append(val)

            packet_len = len(pulses)
            packet = [38, 0, packet_len & 255, packet_len >> 8 & 255, *pulses]
            b64_code = base64.b64encode(bytes(packet)).decode("utf-8")
            command_payload = f"b64:{b64_code}"

        elif self._encoding == "pronto":
            # Pronto Hex encoding (for Xiaomi MiIO IR remotes, etc.)
            frequency = 38000
            freq_div = round(1000000 / (frequency * 0.241246))
            freq_hex = f"{freq_div:04x}"

            timings = [abs(t) for t in raw_timings]
            if len(timings) % 2 != 0:
                timings.append(0)

            num_pairs = len(timings) // 2
            pronto_parts = ["0000", freq_hex, f"{num_pairs:04x}", "0000"]

            cycle_time = 1000000 / frequency
            for t in timings:
                cycles = round(t / cycle_time)
                cycles = max(1, min(65535, cycles))
                pronto_parts.append(f"{cycles:04x}")

            command_payload = " ".join(pronto_parts)

        else:
            # Raw microsecond timing array (for ESPHome/GPIO)
            command_payload = [abs(t) for t in raw_timings]

        # Transmit command to traditional remote entity
        await self.hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": self._remote_entity, "command": command_payload},
            blocking=False,
            context=self._context,
        )

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
    name = config.get("name", "日立冷氣")
    remote_entity = config.get("remote_entity")
    temp_sensor = config.get("temperature_sensor")  # 外部溫度感測器實體 ID
    humidity_sensor = config.get("humidity_sensor")  # 外部濕度感測器實體 ID
    encoding = config.get("encoding", "broadlink")  # broadlink, pronto, raw
    unique_id = config.get("unique_id")
    protocol = config.get("protocol", "ac344")
    cool_only = config.get("cool_only", False)  # 是否為冷專空調 (預設為 False 冷暖)
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
    name = config.get("name", "日立冷氣")
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
    def __init__(
        self,
        hass,
        name,
        remote_entity,
        temp_sensor=None,
        humidity_sensor=None,
        encoding="broadlink",
        unique_id=None,
        protocol="ac344",
        cool_only=False,
    ) -> None:
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

        # 同步底層的溫度極限
        self._attr_min_temp = hitachi.MIN_TEMP
        self._attr_max_temp = hitachi.MAX_TEMP
        self._attr_temperature_unit = "°C"
        self._attr_target_temperature_step = 1

        # 宣告支援的模式 (根據是否冷專決定是否加入暖氣模式)
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.AUTO,
        ]
        if not self._cool_only:
            self._attr_hvac_modes.append(HVACMode.HEAT)

        # 宣告支援的擺風模式 (上下擺風)
        self._attr_swing_modes = [SWING_OFF, SWING_VERTICAL]

        # 宣告支援的左右擺風模式 (7 段去重為 6 種狀態)
        self._attr_swing_horizontal_modes = [
            "auto",
            "right_max",
            "right",
            "middle",
            "left",
            "left_max",
        ]

        # 初始狀態設定
        self._attr_hvac_mode = HVACMode.COOL
        self._attr_target_temperature = 26
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        self._attr_swing_horizontal_mode = "middle"

        # 進階功能暫存器 (定時、防霉)
        self._on_timer_mins = None
        self._off_timer_mins = None
        self._mold_prevention = False
        self._mold_duration = hitachi.HitachiAcMoldDuration.MINS_30

        # 初始化動態屬性與限制
        self._update_supported_limits()

    def _update_supported_limits(self) -> None:
        """根據目前的 HVAC 模式，動態調整支援的功能與風速選項."""
        mode = self._attr_hvac_mode

        if mode == HVACMode.FAN_ONLY:
            # 送風模式不支援調整溫度
            self._attr_supported_features = (
                ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )
            # 送風風量只有 強、弱、微、靜音 (不含自動)
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
            # 自控模式風量只有 自動、微、靜音
            self._attr_fan_modes = [FAN_AUTO, FAN_LOW, "silent"]
            if self._attr_target_temperature is None:
                self._attr_target_temperature = 25  # 設為基準室溫 25
            if self._attr_fan_mode not in self._attr_fan_modes:
                self._attr_fan_mode = FAN_AUTO

        elif mode == HVACMode.DRY:
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )
            # 除濕模式風量只有 微、靜音
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
        """當實體被加入到 hass 時，設定外部溫度與濕度感測器監聽器."""
        await super().async_added_to_hass()

        if self._temp_sensor:
            # 取得初始狀態
            state = self.hass.states.get(self._temp_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                with contextlib.suppress(ValueError):
                    self._attr_current_temperature = float(state.state)

            # 監聽狀態變更
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
            # 取得初始狀態
            state = self.hass.states.get(self._humidity_sensor)
            if state and state.state not in ["unknown", "unavailable"]:
                with contextlib.suppress(ValueError):
                    self._attr_current_humidity = float(state.state)

            # 監聽狀態變更
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
        """UI 調整溫度時觸發."""
        if ATTR_TEMPERATURE in kwargs:
            self._attr_target_temperature = int(kwargs[ATTR_TEMPERATURE])
            self._last_button = hitachi.HitachiAcButton.TEMPERATURE
            await self.async_send_ir_command()

    async def async_set_hvac_mode(self, hvac_mode) -> None:
        """UI 切換模式或開關機時觸發."""
        if self._cool_only and hvac_mode == HVACMode.HEAT:
            _LOGGER.error("冷專空調不支援暖氣模式！")
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
        """UI 切換風速時觸發."""
        self._attr_fan_mode = fan_mode
        self._last_button = hitachi.HitachiAcButton.FAN
        await self.async_send_ir_command()

    async def async_set_swing_mode(self, swing_mode) -> None:
        """UI 切換上下擺風時觸發."""
        self._attr_swing_mode = swing_mode
        self._last_button = hitachi.HitachiAcButton.SWING_V
        await self.async_send_ir_command()

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode) -> None:
        """UI 切換左右擺風時觸發."""
        self._attr_swing_horizontal_mode = swing_horizontal_mode
        self._last_button = hitachi.HitachiAcButton.SWING_H
        await self.async_send_ir_command()

    async def async_set_timer(self, minutes: int) -> None:
        """簡易定時預約：開機時預約關機，關機時預約開機."""
        if self._attr_hvac_mode == HVACMode.OFF:
            # 關機時設定 = 預約開機
            self._on_timer_mins = minutes
            self._off_timer_mins = None
        else:
            # 開機時設定 = 預約關機
            self._off_timer_mins = minutes
            self._on_timer_mins = None

        self._last_button = hitachi.HitachiAcButton.OFF_TIMER
        await self.async_send_ir_command()

    async def async_cancel_timer(self) -> None:
        """取消定時預約."""
        self._on_timer_mins = None
        self._off_timer_mins = None
        self._last_button = hitachi.HitachiAcButton.CANCEL_TIMER
        await self.async_send_ir_command()

    async def async_run_clean(self) -> None:
        """啟動凍結洗淨 (限關機停機狀態)."""
        if self._attr_hvac_mode != HVACMode.OFF:
            _LOGGER.error("凍結洗淨只能在關機狀態下執行！")
            return
        self._last_button = hitachi.HitachiAcButton.CLEAN
        await self.async_send_ir_command()

    async def async_set_mold_prevention(self, active: bool, duration: int = 30) -> None:
        """設定機體防霉功能與防霉時間 (限冷氣與除濕模式下)."""
        if self._attr_hvac_mode not in [HVACMode.COOL, HVACMode.DRY]:
            _LOGGER.error("機體防霉功能僅能在冷氣或除濕模式下啟用！")
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
        """將 HA 狀態轉譯為 Hitachi 協議並發射."""
        is_on = self._attr_hvac_mode != HVACMode.OFF

        # 模式對應
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

        # 【重點 3：風量對應】完整對應 5 段風速
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

        # 溫度對應
        if current_mode == hitachi.HitachiAcMode.AUTO:
            # 自動模式：基於當下室溫決定偏移量 (溫差 = 設定目標溫度 - 當下室溫)
            base_temp = (
                self._attr_current_temperature
                if self._attr_current_temperature is not None
                else 25
            )
            temp_offset = round(self._attr_target_temperature - base_temp)
            target_temp = max(-3, min(3, temp_offset))
        elif current_mode == hitachi.HitachiAcMode.FAN_ONLY:
            # 送風模式不發送溫度值 (傳入冷氣預設 27°C 作為填充以符合 Skeleton 要求，但 UI 不會顯示)
            target_temp = 27
        else:
            target_temp = self._attr_target_temperature

        # 擺動與左右擺風狀態
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

        # 確定發射按鍵碼
        button_code = hitachi.HitachiAcButton.POWER if not is_on else self._last_button

        _LOGGER.warning(
            f"發送指令: 模式 {self._attr_hvac_mode}, 溫度 {target_temp}, 風量 {self._attr_fan_mode}, 上下擺風 {self._attr_swing_mode}, 左右擺風 {self._attr_swing_horizontal_mode}, 按鍵 {button_code.name}"
        )

        # 實例化指令物件 (支援未來透過 protocol 擴充不同型號協定)
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

        # 若是新版 HA 的 `infrared` 實體，直接透過內建的 `async_send_command` 傳遞 command 物件
        if self._remote_entity.startswith("infrared."):
            await infrared.async_send_command(
                self.hass, self._remote_entity, command, context=self._context
            )
            return

        # 取得微秒並進行編碼轉換 (傳統的 remote 實體)
        raw_timings = command.get_raw_timings()

        if self._encoding == "broadlink":
            # Broadlink Base64 編碼
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
            # Pronto Hex 編碼 (適用於小米紅外線/Xiaomi MiIO 遙控器等)
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
            # 原始微秒整數陣列 (適用於 ESPHome/GPIO 等)
            command_payload = [abs(t) for t in raw_timings]

        # 發射到傳統的 remote 實體上
        await self.hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": self._remote_entity, "command": command_payload},
            blocking=False,
            context=self._context,
        )

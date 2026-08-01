# Hitachi Infrared Remote Integration for Home Assistant

<p align="center">
  <img src="custom_components/hitachi_infrared/logo.png" width="160" alt="Hitachi IR Logo" />
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/petercpg/hitachi_infrared)](https://github.com/petercpg/hitachi_infrared/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom component that provides comprehensive climate control for **Hitachi Air Conditioners** via IR remote controls (Broadlink, Xiaomi MiIO / Pronto, ESPHome, or native HA Infrared transmitters).

This integration features a self-contained 344-bit protocol engine (`protocol.py`) built upon Home Assistant's standard `infrared-protocols` architecture, generating exact Hitachi AC IR timings dynamically without relying on bloated static code tables.

---

## ✨ Features

- 🌡️ **Full Climate Control**: Supports Cooling, Heating, Dehumidification (Dry), Fan Only, and Auto modes.
- 🌀 **Multi-Stage Fan & Swing**: Full 5-stage fan speeds (Auto, High, Medium, Low, Silent), 2-stage vertical swing, and configurable horizontal swing (`simple` 2-stage vs `multi_step` 6-stage).
- 🌙 **Preset Modes**: Includes `Eco`, `Sleep` (舒眠), `Comfort` (舒適), and `Moisturizing` (保濕) presets.
- 🎛️ **Auxiliary Control Entities**: Optional select entities (Display Brightness 4-level, Mold Prevention Duration), switches (Mold Prevention / Ionization), and buttons (Frost Wash, PM2.5 Display Toggle).
- 📡 **Universal Emitter Compatibility**: Supports native HA `infrared` transmitters, Broadlink Base64 (`b64:`), Pronto Hex, and Raw Microsecond timings (ESPHome/GPIO).
- 🌡️💧 **External Sensor Binding**: Bind external temperature and humidity sensor entities for real-time room ambient tracking.
- 🔄 **State Restoration**: Persists HVAC mode, target temperature, fan speed, swing settings, and presets across Home Assistant restarts.
- 🛠️ **Custom Services**: Entity services for Display Brightness (`set_display`), PM2.5 Toggle (`set_pm25`), On/Off Timers (`set_timer`, `cancel_timer`), Sleep Timer (`set_sleep_timer`), Mold Prevention (`set_mold_prevention`), and Clean Cycle (`run_clean`).
- ⚙️ **Configurable Feature Toggles**: Enable or disable optional UI cards and controls (Timers, Display Brightness, Somatosensory, Mold Prevention, Frost Wash, PM2.5) directly in Config Flow / Options Flow.
- 🔔 **Debug Toast Notifications**: Live UI toast popups showing full payload parameters when DEBUG logging is active.
- 🌐 **Multi-Language Support**: Fully localized in English (`en`) and Traditional Chinese (`zh-Hant`).

---

## 🗺️ Compatibility Matrix

This integration uses a modular protocol engine designed to support various Hitachi IR remotes and emitters.

| Category | Verified & Supported |
| :--- | :--- |
| **Protocol** | `ac344` (344-bit / 43 Bytes) |
| **IR Emitters** | Native HA `infrared`, Broadlink (RM4/RM Pro), Xiaomi MiIO IR |
| **Device Types** | Air Conditioners (`climate`), Selects, Switches, Buttons |

> ⚠️ **Disclaimer & Community Contributions**
>
> This integration is primarily developed and verified on **Hitachi split-type (HV)AC units using the `ac344` protocol**.
>
> While the codebase is designed to support other Hitachi protocols, devices, and IR emitters, **the maintainer does not own every hardware combination to verify compatibility**.
> - **Tested successfully on your model?** Please open a [GitHub Issue or Discussion](https://github.com/petercpg/hitachi_infrared/issues) to let us know so we can update the tested device matrix!

---

## 📦 Installation

### Option 1: Via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant.
2. Open HACS ➔ **Integrations**.
3. Click the three dots in the top right corner ➔ **Custom repositories**.
4. Add Repository URL: `https://github.com/petercpg/hitachi_infrared`, Category: **Integration**.
5. Search for **Hitachi Infrared Remote Integration** and click **Download**.
6. Restart Home Assistant.

### Option 2: Manual Installation

1. Download the latest release source code.
2. Copy the `custom_components/hitachi_infrared` directory to your Home Assistant's `config/custom_components/` directory.
3. Restart Home Assistant.

---

## ⚙️ Configuration

### Method 1: UI Configuration (Config Flow & Options Flow)

1. In Home Assistant, go to **Settings ➔ Devices & Services**.
2. Click **Add Integration** and search for **Hitachi Infrared Remote**.
3. Fill in the setup form:
   - **Name (Optional)**: e.g., `Living Room AC`.
   - **Infrared / Remote Entity**: Select your transmitter (e.g., `remote.broadlink_rm4_mini` or `remote.xiaomi_ir_remote`).
   - **IR Signal Encoding**: Choose `Broadlink Base64`, `Pronto Hex (Xiaomi / MiIO)`, or `Raw Microseconds (ESPHome)`.
   - **Temperature / Humidity Sensors (Optional)**: Select ambient sensors for room tracking.
   - **Cool Only**: Check if your AC is a cooling-only unit (hides HEAT mode).
   - **Horizontal Swing Mode**: Choose `Simple (Off / Auto)` or `Multi-Step (6 positions)`.
   - **Feature Toggles**: Selectively enable or disable Timers, Display Control, Somatosensory Mode, Mold Prevention, Frost Wash, or PM2.5 display.

> 💡 **Re-configuring Options**:
> Click **Configure** on the integration card anytime to change emitters, encoding, sensors, or feature toggles. All updates take effect **instantly** without restarting Home Assistant.

### Method 2: YAML Configuration

Add the following to your `configuration.yaml`:

```yaml
climate:
  - platform: hitachi_infrared
    name: "Living Room AC"
    remote_entity: "remote.broadlink_rm4_mini"
    encoding: "broadlink" # broadlink, pronto, or raw
    temperature_sensor: "sensor.living_room_temperature"
    humidity_sensor: "sensor.living_room_humidity"
    cool_only: false
    h_swing_mode: "simple" # simple or multi_step
    enable_timer: true
    enable_display_control: true
    enable_somatosensory: false
    enable_mold_prevention: true
    enable_frost_wash: true
    enable_pm25: false
```

---

## 🛠️ Custom Entity Services

This integration registers custom Home Assistant services for advanced Hitachi AC features:

| Service | Action Description | Parameters |
| :--- | :--- | :--- |
| `hitachi_infrared.set_display` | Set indoor LCD panel display brightness | `display` (`bright`, `medium`, `dim`, `off`) |
| `hitachi_infrared.set_pm25` | Toggle PM2.5 concentration reading on panel | None |
| `hitachi_infrared.set_timer` | Schedule On/Off timer duration | `minutes` (positive integer, 1..1440) |
| `hitachi_infrared.cancel_timer` | Cancel active scheduled timer | None |
| `hitachi_infrared.set_sleep_timer` | Activate sleep mode and optional timer | `minutes` (optional, positive integer) |
| `hitachi_infrared.run_clean` | Trigger Frost Wash / Clean Cycle (凍結洗淨) | None (allowed when AC is OFF) |
| `hitachi_infrared.set_mold_prevention` | Enable/disable Mold Prevention (機體防霉) | `active` (boolean), `duration` (10, 20, 30, 45, 60) |

---

## 🔍 Debugging & Live Toast Notifications

To enable verbose debug logging for this integration, add the following to your `configuration.yaml` or use **Enable Debug Logging** on the integration page:

```yaml
logger:
  default: info
  logs:
    custom_components.hitachi_infrared: debug
```

When DEBUG mode is enabled:
1. Integration startup prints integration and base `infrared-protocols` package version to the logs.
2. Every transmitted IR action triggers a **Live Toast Notification** popup in the Home Assistant UI detailing the exact parameters sent!

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

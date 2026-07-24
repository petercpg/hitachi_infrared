# Hitachi Infrared Remote Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/petercpg/hitachi_infrared)](https://github.com/petercpg/hitachi_infrared/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom component that provides comprehensive climate control for Hitachi Air Conditioners and Infrared Remotes via IR blasters (Broadlink, Xiaomi MiIO / Pronto, ESPHome, or native HA Infrared transmitters).

---

## ✨ Features

- 🌡️ **Full Climate Control**: Supports Cooling, Heating, Dehumidification (Dry), Fan Only, and Auto modes.
- 🌀 **Multi-Stage Fan & Swing**: Full 5-stage fan speeds (Auto, High, Medium, Low, Silent) and vertical / 6-stage horizontal swing control.
- 📡 **Universal Emitter Compatibility**: Supports native HA `infrared` transmitters, Broadlink Base64 (`b64:`), Pronto Hex, and Raw Microsecond timings (ESPHome/GPIO).
- 🌡️💧 **External Sensor Binding**: Bind external temperature and humidity sensor entities for real-time room ambient tracking.
- ⏱️ **Timer & Special Functions**: Supports Off-Timer / On-Timer scheduling, Mold Prevention (防霉), and Clean Cycle (凍結洗淨).
- 🌐 **Multi-Language Support**: Fully localized in English (`en`) and Traditional Chinese (`zh-Hant`).
- ⚙️ **Config Flow & YAML**: Easy UI configuration via Config Flow or traditional `configuration.yaml`.

---

## 🛠️ Supported Protocols

This integration utilizes the [`infrared-protocols`](https://github.com/petercpg/infrared-protocols) library:
- **`ac344` (Default & Current Supported Protocol)**: 344-bit (43 Bytes) frame format used by most Taiwanese Hitachi AC remotes.


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

### Method 1: UI Configuration (Config Flow)

1. In Home Assistant, go to **Settings ➔ Devices & Services**.
2. Click **Add Integration** and search for **Hitachi Infrared Remote**.
3. Fill in the setup form:
   - **Name (Optional)**: e.g., `Living Room AC` (defaults to localized `Hitachi AC` / `日立冷氣`).
   - **Infrared / Remote Entity**: Select your transmitter entity (e.g., `remote.broadlink_rm4_mini`).
   - **Temperature Sensor Entity (Optional)**: Select your external temperature sensor (e.g., `sensor.living_room_temperature`).
   - **Humidity Sensor Entity (Optional)**: Select your external humidity sensor (e.g., `sensor.living_room_humidity`).
   - **Cool Only**: Check if your AC is a cooling-only unit (hides HEAT mode).



### Method 2: YAML Configuration

Add the following snippet to your `configuration.yaml`:

```yaml
climate:
  - platform: hitachi_infrared
    name: "Living Room AC"
    remote_entity: "remote.broadlink_rm4_mini"
    temperature_sensor: "sensor.living_room_temperature"
    humidity_sensor: "sensor.living_room_humidity"
    encoding: "broadlink" # broadlink, pronto, or raw
    cool_only: false
```

---

## 🔍 Debugging & System Logs

To enable verbose debug logging for this integration, add the following to your `configuration.yaml` or use the **Enable Debug Logging** option under **Settings ➔ Devices & Services ➔ Hitachi Infrared Remote ➔ (...)**:

```yaml
logger:
  default: info
  logs:
    custom_components.hitachi_infrared: debug
```

When enabled, integration startup logs will print version and Git commit information for `infrared-protocols`:

```text
DEBUG [custom_components.hitachi_infrared] Loaded infrared-protocols: version=8.2.0, path=..., git_url=https://github.com/petercpg/infrared-protocols.git, ref=add-hitachi-ac344, commit=04702a6de226e7667e8bb72c2732fcdd5e26f53a
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

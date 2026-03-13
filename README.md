# TiltScan-Bleak

A Python-based Tilt hydrometer scanner app using the Bleak library for Bluetooth Low Energy (BLE) scanning on Windows.

## Overview

TiltScan-Bleak is a lightweight web-based application that scans for Tilt hydrometers via Bluetooth and provides real-time data through a REST API. The app runs an on-demand scanning service that activates only when needed, minimizing power consumption while keeping sensor data current.

**Key Features:**
- On-demand Bluetooth scanning (3.3-second scan windows)
- REST API for retrieving sensor data
- Optional CSV logging of sensor readings
- Web server on port 1880 with multiple endpoints
- Standalone Windows executable included

## Getting Started

### Option 1: Standalone Executable (Windows)
Download the `.exe` file from the repository and run it directly. No Python installation required.

```bash
TiltScan-Bleak.exe
```

The server will start and listen on `http://127.0.0.1:1880/`

### Option 2: Python Script
If you prefer to run the Python script directly, you'll need Python 3.7+ and the required dependencies.

```bash
pip install bleak beacontools aiohttp
python tilt-scan.py
```

## API Endpoints

Once running, the server provides the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/data` | GET | Triggers a 3.3-second scan and returns current sensor data as JSON |
| `/logging/enable` | GET | Enable CSV logging of sensor readings |
| `/logging/disable` | GET | Disable CSV logging (data collection continues) |
| `/logging/status` | GET | Check current logging status |
| `/shutdown` | GET | Gracefully shut down the application |

## Usage Examples

**Get Sensor Data:**
```bash
curl http://127.0.0.1:1880/data
```

Response includes timestamp, temperature, specific gravity, color, and other Tilt sensor data.

**Enable CSV Logging:**
```bash
curl http://127.0.0.1:1880/logging/enable
```

**Check Logging Status:**
```bash
curl http://127.0.0.1:1880/logging/status
```

**Shutdown:**
```bash
curl http://127.0.0.1:1880/shutdown
```

## How It Works

- **On-Demand Scanning**: When you request `/data`, the app performs a 3.3-second Bluetooth scan and returns the most recent sensor readings before stopping the scan.
- **CSV Logging**: If enabled, sensor data is automatically logged to CSV files every 15 minutes. If no `/data` requests are made within 15 minutes, the app initiates an automatic scan for CSV logging purposes.
- **Efficient Operation**: The Bluetooth scanner is only active during scan windows, reducing CPU and power usage compared to continuous scanning.

## Output Files

Sensor data is saved to CSV files in the following format:
```
TILT-[COLOR]-[MAC-ADDRESS].csv
```

Example:
```
TILT-RED-EC-23-93-76-B6-1C.csv
TILT-ORANGE-C2-71-6C-C5-2B-E2.csv
```

Each CSV file contains columns for Timestamp, Timepoint, SG, Temp, Color, Beer, and Comment.

## Requirements

- Windows 10 or later (for Bluetooth support)
- Python 3.7+ (if running from source)
- Bluetooth-capable hardware

## Dependencies (Python)

- `bleak` - Bluetooth Low Energy library
- `beacontools` - iBeacon packet parsing
- `aiohttp` - Async HTTP web framework

## License

See LICENSE file for details.

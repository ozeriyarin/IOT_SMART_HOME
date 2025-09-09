# HouseKeyper – IoT Smart Home Safety (course project)

A minimal, fully runnable stack that meets the rubric:
- **3 emulator types** (sensors: DHT/env, leak; actuator: button/knob; **relay** device that reacts to commands)
- **Data manager app**: subscribes to MQTT, writes to SQLite, runs rules, publishes warnings/alarms
- **GUI app**: Streamlit dashboard with live status and alerts; buttons to toggle a relay
- **Local DB**: SQLite (`housekeyper.db`)

## Quick start
1) Start broker (Docker required):
```bash
docker compose up -d
```
2) Create a venv and install deps:
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r emulators/requirements.txt -r data_manager/requirements.txt -r gui/requirements.txt
```
3) Run the data manager:
```bash
export BROKER_HOST=localhost  # Windows PowerShell: $env:BROKER_HOST="localhost"
python data_manager/app.py
```
4) In a new terminal, run a few emulators (each is optional; run as many as you like):
```bash
python emulators/dht_emulator.py --device-id dht-1 --room kitchen
python emulators/leak_emulator.py --device-id leak-1 --room bathroom
python emulators/stove_emulator.py --device-id stove-1 --room kitchen
python emulators/button_emulator.py --device-id btn-1 --room kitchen
python emulators/relay_emulator.py --device-id relay-1 --room kitchen
```
5) Launch the GUI:
```bash
streamlit run gui/streamlit_app.py
```
Open the URL Streamlit prints (usually http://localhost:8501).

## Topics & message schema
All telemetry is published on `hk/telemetry/<device_id>` with a JSON payload like:
```json
{
  "device_id": "dht-1",
  "class": "sensor",
  "type": "environment",
  "model": "DHT22",
  "location": "kitchen",
  "ts": "2025-01-01T12:00:00Z",
  "metrics": { "temperature_c": 24.6, "humidity": 44.1 }
}
```
Relay control:
- Command topic: `hk/actuators/relay/<device_id>/cmd` with `{"command": "ON"|"OFF"}`
- State topic:   `hk/actuators/relay/<device_id>/state` (published by relay emulator)

Alerts are published by the data manager on `hk/alerts` with payload like:
```json
{ "ts":"...","level":"WARNING","code":"HIGH_TEMP","message":"Kitchen > 30°C","device_id":"dht-1","room":"kitchen" }
```

## Simple rules (editable in `data_manager/app.py`)
- **LEAK_DETECTED**: any leak metric true → CRITICAL
- **STOVE_UNATTENDED**: stove_on true and last button press in the same room was >10 min ago, or surface temp > 80°C → WARNING
- **HIGH_TEMP**: temperature_c > 30°C → WARNING

## Project layout
```
housekeyper/
  docker-compose.yml
  broker/mosquitto.conf
  data_manager/
    app.py
    requirements.txt
  emulators/
    dht_emulator.py
    leak_emulator.py
    stove_emulator.py
    button_emulator.py
    relay_emulator.py
    requirements.txt
  gui/
    streamlit_app.py
    requirements.txt
  db/schema.sql
  .env.sample
  README.md
```

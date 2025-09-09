import os, json, sqlite3, datetime
from typing import Dict, Any
import paho.mqtt.client as mqtt

DB_PATH = os.getenv("HK_DB_PATH", "housekeyper.db")
BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

CONN = db()

def init_db():
    with open(os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql"), "r", encoding="utf-8") as f:
        CONN.executescript(f.read())
    CONN.commit()

def upsert_device(d: Dict[str, Any]):
    CONN.execute(
        '''INSERT INTO devices(device_id,class,type,model,location,last_seen)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(device_id) DO UPDATE SET class=excluded.class, type=excluded.type, model=excluded.model, location=excluded.location, last_seen=excluded.last_seen''',
        (d.get("device_id"), d.get("class"), d.get("type"), d.get("model"), d.get("location"), d.get("ts"))
    )
    CONN.commit()

def insert_reading(device_id: str, ts: str, key: str, value: Any):
    if not isinstance(value, (int, float, str)):
        value = json.dumps(value)
    CONN.execute("INSERT INTO readings(device_id, ts, key, value) VALUES(?,?,?,?)",
                 (device_id, ts, key, str(value)))
    CONN.commit()

def insert_alert(ts: str, level: str, code: str, message: str, device_id: str, room: str):
    CONN.execute("INSERT INTO alerts(ts, level, code, message, device_id, room) VALUES(?,?,?,?,?,?)",
                 (ts, level, code, message, device_id, room))
    CONN.commit()

def iso_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

LAST_BUTTON_PRESS: Dict[str, datetime.datetime] = {}

def evaluate_rules(msg: Dict[str, Any], client: mqtt.Client):
    device_id = msg.get("device_id","")
    room      = msg.get("location","unknown")
    ts        = msg.get("ts", iso_now())
    metrics   = (msg.get("metrics") or {})
    dev_type  = msg.get("type")

    if dev_type == "leak" and metrics.get("leak"):
        alert = {"ts": ts, "level": "CRITICAL", "code": "LEAK_DETECTED",
                 "message": f"Leak detected in {room}", "device_id": device_id, "room": room}
        insert_alert(**alert)
        client.publish("hk/alerts", json.dumps(alert))

    if dev_type == "button" and metrics.get("pressed"):
        LAST_BUTTON_PRESS[room] = datetime.datetime.utcnow()

    if dev_type == "stove":
        on   = bool(metrics.get("stove_on"))
        surf = float(metrics.get("surface_temp_c", 0.0))
        last_btn = LAST_BUTTON_PRESS.get(room, None)
        too_long = (last_btn is None) or ((datetime.datetime.utcnow() - last_btn) > datetime.timedelta(minutes=10))
        if on and (surf > 80.0 or too_long):
            reason = "high surface temp" if surf > 80.0 else "no presence (button) >10 min"
            alert = {"ts": ts, "level": "WARNING", "code": "STOVE_UNATTENDED",
                     "message": f"Stove in {room} may be unattended ({reason})", "device_id": device_id, "room": room}
            insert_alert(**alert)
            client.publish("hk/alerts", json.dumps(alert))

    if dev_type == "environment":
        temp = float(metrics.get("temperature_c", 0.0))
        if temp > 30.0:
            alert = {"ts": ts, "level": "WARNING", "code": "HIGH_TEMP",
                     "message": f"{room.capitalize()} > 30°C", "device_id": device_id, "room": room}
            insert_alert(**alert)
            client.publish("hk/alerts", json.dumps(alert))

def on_message(client, _userdata, msg):
    try:
        topic = msg.topic
        raw = json.loads(msg.payload.decode("utf-8"))

        if topic.startswith("hk/telemetry/"):
            payload = raw  

        elif topic.startswith("hk/actuators/relay/") and topic.endswith("/state"):
            # topic: hk/actuators/relay/<device_id>/state
            parts = topic.split("/")
            device_id = parts[3] if len(parts) >= 5 else raw.get("device_id", "relay-unknown")
            room = raw.get("room", "unknown")
            state = raw.get("state", "UNKNOWN")
            payload = {
                "device_id": device_id,
                "class": "actuator",
                "type": "relay",
                "model": "HK-RELAY",
                "location": room,
                "ts": iso_now(),
                "metrics": {"state": state}
            }
        else:
            return

        upsert_device(payload)
        ts = payload.get("ts", iso_now())
        for k, v in (payload.get("metrics") or {}).items():
            insert_reading(payload.get("device_id",""), ts, k, v)
        evaluate_rules(payload, client)
        print(f"[INGEST] {topic} -> ok")

    except Exception as e:
        print("[ERROR]", e)


def main():
    init_db()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe("hk/telemetry/+")
    client.subscribe("hk/actuators/relay/+/state")
    print(f"[DATA-MANAGER] mqtt://{BROKER_HOST}:{BROKER_PORT} | db={DB_PATH}")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

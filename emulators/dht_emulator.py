import argparse, json, os, time, random, datetime
import paho.mqtt.client as mqtt

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def publish_loop(topic, payload_fn, host, port, period):
    client = mqtt.Client()
    client.connect(host, port, 60)
    try:
        while True:
            payload = payload_fn()
            client.publish(topic, json.dumps(payload), qos=0, retain=False)
            print(f"[PUB] {topic} -> {payload}")
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()

def common_args():
    p = argparse.ArgumentParser()
    p.add_argument("--device-id", required=True)
    p.add_argument("--room", required=True)
    p.add_argument("--host", default=os.getenv("BROKER_HOST","localhost"))
    p.add_argument("--port", default=int(os.getenv("BROKER_PORT","1883")), type=int)
    p.add_argument("--period", type=float, default=2.0)
    return p

if __name__ == "__main__":
    args = common_args().parse_args()
    topic = f"hk/telemetry/{args.device_id}"
    def build():
        temp = round(random.uniform(21.0, 33.0), 1)
        hum  = round(random.uniform(35.0, 65.0), 1)
        return {
            "device_id": args.device_id,
            "class": "sensor",
            "type": "environment",
            "model": "DHT22",
            "location": args.room,
            "ts": now_iso(),
            "metrics": {"temperature_c": temp, "humidity": hum}
        }
    publish_loop(topic, build, args.host, args.port, args.period)

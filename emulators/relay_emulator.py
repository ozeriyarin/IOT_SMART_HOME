import argparse, json, os, datetime
import paho.mqtt.client as mqtt

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--device-id", required=True)
    p.add_argument("--room", required=True)
    p.add_argument("--host", default=os.getenv("BROKER_HOST","localhost"))
    p.add_argument("--port", default=int(os.getenv("BROKER_PORT","1883")), type=int)
    args = p.parse_args()

    topic_cmd = f"hk/actuators/relay/{args.device_id}/cmd"
    topic_state = f"hk/actuators/relay/{args.device_id}/state"

    client = mqtt.Client()
    client.connect(args.host, args.port, 60)

    state = {"device_id": args.device_id, "room": args.room, "ts": now_iso(), "state": "OFF"}

    def publish_state():
        state["ts"] = now_iso()
        client.publish(topic_state, json.dumps(state), qos=0, retain=True)
        print(f"[RELAY] state -> {state}")

    def on_msg(_c, _u, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            cmd = str(payload.get("command","")).upper()
            if cmd in ("ON","OFF"):
                state["state"] = cmd
                publish_state()
            else:
                print("[RELAY] unknown command:", payload)
        except Exception as e:
            print("[RELAY] error:", e)

    client.on_message = on_msg
    client.subscribe(topic_cmd)
    publish_state()
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass

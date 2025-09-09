import os, sqlite3, pandas as pd, json
import streamlit as st
import paho.mqtt.client as mqtt

DB_PATH = os.getenv("HK_DB_PATH", "housekeyper.db")
BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))

st.set_page_config(page_title="HouseKeyper", layout="wide")
st.title("🏠 HouseKeyper — Smart Home Safety Dashboard")

@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

@st.cache_resource
def get_mqtt():
    c = mqtt.Client()
    c.connect(BROKER_HOST, BROKER_PORT, 60)
    return c

db = get_db()
mqttc = get_mqtt()

col1, col2 = st.columns([2,1], gap="large")

with col1:
    st.subheader("📟 Devices")
    devices = pd.read_sql_query("SELECT * FROM devices ORDER BY location, device_id", db)
    st.dataframe(devices, use_container_width=True, height=260)

    st.subheader("📈 Latest readings")
    latest = pd.read_sql_query(
        '''
        SELECT r.device_id, d.location, r.key, r.value, r.ts
          FROM readings r
          JOIN (
            SELECT device_id, key, MAX(ts) AS max_ts
              FROM readings
             GROUP BY device_id, key
          ) mx ON r.device_id=mx.device_id AND r.key=mx.key AND r.ts=mx.max_ts
          JOIN devices d ON d.device_id=r.device_id
         ORDER BY d.location, r.device_id, r.key
        ''', db
    )
    st.dataframe(latest, use_container_width=True, height=300)

with col2:
    st.subheader("🚨 Alerts (latest 50)")
    alerts = pd.read_sql_query("SELECT * FROM alerts ORDER BY ts DESC LIMIT 50", db)
    st.dataframe(alerts, use_container_width=True, height=400)

    st.subheader("🔌 Relay control")
    relay_id = st.text_input("Relay device_id", value="relay-1")
    cmd = st.selectbox("Command", ["ON","OFF"])
    if st.button("Send"):
        topic = f"hk/actuators/relay/{relay_id}/cmd"
        payload = json.dumps({"command": cmd})
        mqttc.publish(topic, payload)
        st.success(f"Sent {cmd} to {topic}")

st.caption(f"DB: {DB_PATH} | Broker: mqtt://{BROKER_HOST}:{BROKER_PORT}")

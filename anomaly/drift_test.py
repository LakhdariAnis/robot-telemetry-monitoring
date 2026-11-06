#!/usr/bin/env python3
import sys
import time
import json
import threading
import paho.mqtt.client as mqtt

MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883

_last_heading = None
_moving = None
_alert = None
_lock = threading.Lock()

def on_message(client, userdata, msg):
    global _last_heading, _moving, _alert
    with _lock:
        if msg.topic == "car/imu":
            try:
                data = json.loads(msg.payload.decode())
                _last_heading = data.get("heading_deg")
                _moving = data.get("moving")
            except:
                pass
        elif msg.topic == "car/anomaly/imu_static_drift":
            try:
                data = json.loads(msg.payload.decode())
                _alert = data.get("severity")
                print(f"\n[ALERT] Anomaly status updated: {data}\n")
            except:
                pass

def main():
    mqttc = mqtt.Client(client_id=f"drift_tester_{time.time()}")
    mqttc.on_message = on_message
    mqttc.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    mqttc.subscribe("car/imu")
    mqttc.subscribe("car/anomaly/imu_static_drift")
    mqttc.loop_start()

    print("Setting sim speed to 50x...")
    mqttc.publish("car/mock/sim_speed", json.dumps({"speed": 50.0}))
    time.sleep(0.5)

    print("Resetting car to start station...")
    mqttc.publish("car/mock/reset", json.dumps({"station": "start"}))
    time.sleep(2)

    print("Injecting imu_static_drift anomaly...")
    mqttc.publish("car/mock/inject", json.dumps({"anomaly": "imu_static_drift", "active": True}))

    start_time = time.time()

    try:
        while True:
            time.sleep(1)
            with _lock:
                h = _last_heading
                m = _moving
                a = _alert

            elapsed = int(time.time() - start_time)
            h_str = f"{h:.2f}" if h is not None else "None"
            print(f"[{elapsed}s] Heading: {h_str} | Moving: {m} | Alert: {a}")
    except KeyboardInterrupt:
        print("\nStopping test...")
    finally:
        mqttc.publish("car/mock/inject", json.dumps({"anomaly": "imu_static_drift", "active": False}))
        mqttc.publish("car/mock/sim_speed", json.dumps({"speed": 1.0}))
        mqttc.loop_stop()
        mqttc.disconnect()

if __name__ == "__main__":
    main()

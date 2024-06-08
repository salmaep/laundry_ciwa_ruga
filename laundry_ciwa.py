import paho.mqtt.client as mqtt
import time
import json
import random
from datetime import datetime, timedelta

broker = "localhost"
topic = "laundry/ciwa"  # Ubah ke "laundry/ruga" untuk laundry_ruga.py
max_weight_quota = 10  # Maksimum berat cucian yang dapat diproses (kg)
current_weight = 0
orders = []

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(topic + "/order")

def on_message(client, userdata, msg):
    global current_weight
    if msg.topic.endswith("/order"):
        order = json.loads(msg.payload.decode())
        client_id = order["client_id"]
        weight = order["weight"]
        package = order["package"]

        # Hitung waktu proses berdasarkan berat dan jenis paket
        process_time_per_kg = {"hemat": 1.5, "standar": 1, "instant": 0.5}[package]
        process_time = weight * process_time_per_kg

        if current_weight + weight <= max_weight_quota:
            current_weight += weight
            finish_time = datetime.now() + timedelta(seconds=process_time)
            orders.append({
                "client_id": client_id,
                "weight": weight,
                "finish_time": finish_time
            })
            print(f"Order received and accepted from {client_id} with {weight} kg package {package}. Current weight: {current_weight}/{max_weight_quota} kg")
            response = {"status": "accepted", "current_weight": current_weight}
        else:
            print(f"Order received but rejected from {client_id}  with {weight} kg package {package}. Weight limit exceeded: {current_weight}/{max_weight_quota} kg")
            response = {"status": "rejected", "current_weight": current_weight}
        client.publish(msg.topic + "/response", json.dumps(response))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, 1883, 60)
client.loop_start()

def process_orders():
    global current_weight
    current_time = datetime.now()
    for order in orders[:]:
        if current_time >= order["finish_time"]:
            orders.remove(order)
            current_weight -= order["weight"]
            print(f"Order completed for {order['client_id']}. Current weight: {current_weight}/{max_weight_quota} kg")

while True:
    pick_up_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    delivery_time = (datetime.now() + timedelta(seconds=random.randint(10, 50))).strftime("%Y-%m-%d %H:%M:%S")
    message = {
        "Pick up": pick_up_time,
        "Delivery": delivery_time,
        "current_weight": current_weight
    }
    client.publish(topic, json.dumps(message))
    process_orders()
    time.sleep(10)

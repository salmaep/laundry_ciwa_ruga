import paho.mqtt.client as mqtt
import time
import json
import random
from datetime import datetime, timedelta

broker = "localhost"
laundry_follows = ["laundry/ciwa", "laundry/ruga"]
client_id = "bot_client_3"
orders = []
order_responses = {}
pending_orders = []

packages = ["hemat", "standar", "instant"]
clients = ["Client 3"]

# Define max weight quotas for each laundry
laundry_max_weights = {
    "ciwa": 10,  # max weight for Laundry Ciwa is 10 kg
    "ruga": 8    # max weight for Laundry Ruga is 8 kg
}

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in laundry_follows:
        client.subscribe(topic)
        client.subscribe(topic + "/order/response")

def on_message(client, userdata, msg):
    print(f"Message from {msg.topic}: {msg.payload.decode()}")
    if msg.topic.endswith("/order/response"):
        response = json.loads(msg.payload.decode())
        order_responses[msg.topic] = response
        process_order_responses()
    else:
        try:
            data = json.loads(msg.payload.decode())
            delivery_time = datetime.strptime(data['Delivery'], "%Y-%m-%d %H:%M:%S")
            current_weight = data.get('current_weight', 0)
            orders.append((msg.topic, delivery_time, current_weight))
            process_orders()
        except Exception as e:
            print(f"Error processing message: {e}")

def process_orders():
    if orders:
        fastest_order = min(orders, key=lambda x: x[1])
        topic, delivery_time, current_weight = fastest_order
        print(f"Fastest delivery by {topic} at {delivery_time} with current weight {current_weight} kg")
        # Simulate placing an order to the laundry with the fastest delivery time
        place_order(topic, current_weight)

def place_order(laundry_topic, current_weight):
    name = random.choice(clients)
    weight = random.randint(1, 5)
    package = random.choice(packages)
    order_topic = laundry_topic + "/order"
    order = {
        "client_id": name,
        "weight": weight,
        "package": package
    }

    # Extract the laundry name from the topic to get the max weight
    laundry_name = laundry_topic.split("/")[1]
    max_weight = laundry_max_weights.get(laundry_name)
    
    if max_weight is None:
        print(f"Error: Max weight for {laundry_name} not found")
        return

    if current_weight is None:
        print(f"Error: Current weight for {laundry_topic} is None")
        return

    if current_weight + weight <= max_weight:
        client.publish(order_topic, json.dumps(order))
        print(f"Order placed to {laundry_topic} by {name} with {weight} kg package {package}")
    else:
        print(f"Order by {name} with {weight} kg package {package} is pending due to full quota")
        pending_orders.append((order, datetime.now() + timedelta(seconds=10)))

def process_order_responses():
    for topic, response in order_responses.items():
        if response['status'] == 'rejected':
            print(f"Order to {topic} was rejected due to full quota. Finding alternative...")
            for i in range(10, 0, -1):
                print(f"Waiting {i} seconds before retry...")
                time.sleep(1)
            orders_to_check = [
                order for order in orders
                if order[2] < laundry_max_weights.get(order[0].split("/")[1], 0) 
                and order[0] != topic.replace("/order/response", "")
            ]
            if orders_to_check:
                alternative_order = min(orders_to_check, key=lambda x: x[1])
                alternative_topic, _, _ = alternative_order
                place_order(alternative_topic, 0)  
            else:
                print("No alternative laundries with available quota. Orders are PENDING.")
    process_pending_orders()

def process_pending_orders():
    current_time = datetime.now()
    for pending_order in pending_orders[:]:
        order, hold_until = pending_order
        if current_time >= hold_until:
            for topic, delivery_time, current_weight in orders:
                laundry_name = topic.split("/")[1]
                max_weight = laundry_max_weights.get(laundry_name)
                if max_weight is None:
                    continue
                if current_weight is None:
                    continue
                if current_weight + order["weight"] <= max_weight:
                    client.publish(topic + "/order", json.dumps(order))
                    pending_orders.remove(pending_order)
                    print(f"Pending order placed to {topic} by {order['client_id']} with {order['weight']} kg package {order['package']}")
                    break

client = mqtt.Client(client_id)
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, 1883, 60)
client.loop_start()

while True:
    process_pending_orders()
    time.sleep(3)
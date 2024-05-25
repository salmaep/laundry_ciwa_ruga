import paho.mqtt.client as mqtt

broker = "localhost"
laundry_follows = ["laundry/ciwa", "laundry/ruga"]

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in laundry_follows:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    print(f"Message from {msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, 1883, 60)
client.loop_forever()

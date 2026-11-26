import json
import paho.mqtt.client as mqtt


class MQTTHandler:
    """MQTT Publisher for sending LED state commands to NodeMCU devices."""

    def __init__(self, broker: str = "broker.mqttdashboard.com", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()

    def start(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_led_state(self, led_id: str, state: str):
        topic = f"led/{led_id}/state"
        payload = json.dumps({"state": state})
        self.client.publish(topic, payload)
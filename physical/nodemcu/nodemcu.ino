#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Wi-Fi credentials
#define WIFI_SSID "ZTE_FD6C6E"
#define WIFI_PASSWORD "IoT-DT20"

// MQTT configuration
const char* mqtt_server = "broker.mqttdashboard.com";
const int mqtt_port = 1883;
const char* mqtt_client_id = "NodeMCU_LED_Client_1";
const char* mqtt_topic = "led/87b566c7-194d-47c3-a07a-e146f979125b/state";

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnectWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi connection lost. Reconnecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
      delay(1000);
      Serial.println("Reconnecting to Wi-Fi...");
    }
    Serial.println("Reconnected to the Wi-Fi network.");
  }
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT broker...");
    if (client.connect(mqtt_client_id)) {
      Serial.println(" connected!");
      client.subscribe(mqtt_topic);
      Serial.print("Subscribed to topic: ");
      Serial.println(mqtt_topic);
    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      Serial.println(" — retrying in 5 seconds");
      delay(5000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  static char msg[256];

  if (length >= sizeof(msg)) {
    length = sizeof(msg) - 1;
  }
  memcpy(msg, payload, length);
  msg[length] = '\0';

  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(msg);

  // Process only messages on topics ending with /state
  if (strstr(topic, "/state") == nullptr) {
    return;
  }

  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, msg);
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }

  const char* state = doc["state"] | "";

  // On NodeMCU (ESP8266), LED_BUILTIN is active-low (LOW = ON, HIGH = OFF)
  if (strcmp(state, "on") == 0) {
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("LED turned ON");
  } else if (strcmp(state, "off") == 0) {
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.println("LED turned OFF");
  } else {
    Serial.print("Unknown state value: ");
    Serial.println(state);
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);  // Start with LED OFF

  Serial.begin(9600);
  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  reconnectWiFi();
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();
}
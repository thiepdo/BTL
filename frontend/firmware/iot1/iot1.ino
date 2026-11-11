#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"

const char* ssid        = "1"; 
const char* password    = "12345678";
const char* mqtt_server = "192.168.250.118"; 
const int   mqtt_port   = 1883;
const char* mqtt_user   = "thiep";
const char* mqtt_pass   = "B23DCCN787";

#define DHTPIN D4
#define DHTTYPE DHT11
#define LDRPIN A0
#define LED1_PIN 14 // D5
#define LED2_PIN 12 // D6

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsg = 0;

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("-> Nhan lenh tu MQTT [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  if (String(topic) == "device/control") {
    if (message == "1_ON") {
      digitalWrite(LED1_PIN, HIGH);
      client.publish("device/status", "{\"deviceId\":1,\"status\":\"SUCCESS\",\"state\":\"ON\"}");
    }
    else if (message == "1_OFF") {
      digitalWrite(LED1_PIN, LOW);
      client.publish("device/status", "{\"deviceId\":1,\"status\":\"SUCCESS\",\"state\":\"OFF\"}");
    }
    else if (message == "2_ON") {
      digitalWrite(LED2_PIN, HIGH);
      client.publish("device/status", "{\"deviceId\":2,\"status\":\"SUCCESS\",\"state\":\"ON\"}");
    }
    else if (message == "2_OFF") {
      digitalWrite(LED2_PIN, LOW);
      client.publish("device/status", "{\"deviceId\":2,\"status\":\"SUCCESS\",\"state\":\"OFF\"}");
    }
    else if (message == "ALL_ON") {
      digitalWrite(LED1_PIN, HIGH);
      digitalWrite(LED2_PIN, HIGH);
      client.publish("device/status", "{\"deviceId\":1,\"status\":\"SUCCESS\",\"state\":\"ON\"}");
      client.publish("device/status", "{\"deviceId\":2,\"status\":\"SUCCESS\",\"state\":\"ON\"}");
    }
    else if (message == "ALL_OFF") {
      digitalWrite(LED1_PIN, LOW);
      digitalWrite(LED2_PIN, LOW);
      client.publish("device/status", "{\"deviceId\":1,\"status\":\"SUCCESS\",\"state\":\"OFF\"}");
      client.publish("device/status", "{\"deviceId\":2,\"status\":\"SUCCESS\",\"state\":\"OFF\"}");
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Dang ket noi MQTT Broker...");
    String clientId = "ESP8266Client-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println(" -> Thanh cong!");
      client.subscribe("device/control");
    } else {
      Serial.print(" -> That bai, rc=");
      Serial.print(client.state());
      Serial.println(". Thu lai sau 2 giay...");
      delay(2000);
    }
  }
}

void setup() {
  // 1. Khởi tạo Serial Baudrate 115200
  Serial.begin(115200);
  delay(10);
  Serial.println("\n--- HE THONG BAT DAU KHOT DONG ---");

  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);
  dht.begin();

  // Kết nối WiFi
  Serial.print("Dang ket noi WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print(".");
  }
  Serial.println("\nWiFi da ket noi!");
  Serial.print("Dia chi IP ESP8266: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) { reconnect(); }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsg > 2000) {
    lastMsg = now;
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    
    // Đảo ngược giá trị ánh sáng bằng map() để Sáng = Giá trị lớn, Tối = Giá trị nhỏ
    int lightVal = map(analogRead(LDRPIN), 0, 1023, 1023, 0); 

    if (!isnan(h) && !isnan(t)) {
      String payload = "{\"temperature\":" + String(t, 1) + ",\"humidity\":" + String(h, 1) + ",\"light\":" + String(lightVal) + "}";
      
      // Gửi lên MQTT Broker
      client.publish("sensor/data", payload.c_str());

      // In dữ liệu ra bảng Serial Monitor của Arduino IDE
      Serial.print("<- Gui du lieu MQTT: ");
      Serial.println(payload);
    }
  }
}
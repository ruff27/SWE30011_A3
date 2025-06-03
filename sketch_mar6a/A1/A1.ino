// Sensor Node
#include <DHT.h>

// Pin definitions
#define DHTPIN 3          // DHT22 data pin
#define DHTTYPE DHT22     // DHT sensor type
#define PIR_PIN 2         // PIR motion sensor
#define LIGHT_PIN A1      // Phototransistor

// Initialize DHT sensor
DHT dht(DHTPIN, DHTTYPE);

// Variables
unsigned long lastReadTime = 0;
const unsigned long READ_INTERVAL = 2000; // 2 seconds for DHT22

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(PIR_PIN, INPUT);
  
  // Wait for sensor stabilization
  delay(2000);
  Serial.println("SENSOR_NODE_READY");
}

void loop() {
  if (millis() - lastReadTime >= READ_INTERVAL) {
    lastReadTime = millis();
    
    // Read DHT22
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    
    // Read phototransistor (0-1023, higher = more light)
    int lightLevel = analogRead(LIGHT_PIN);
    
    // Read PIR sensor (HIGH = motion detected)
    int motionDetected = digitalRead(PIR_PIN);
    
    // Check if DHT readings are valid
    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("ERROR:DHT_READ_FAILED");
    } else {
      // Send data in JSON format for easier parsing
      Serial.print("{");
      Serial.print("\"temp\":");
      Serial.print(temperature);
      Serial.print(",\"humidity\":");
      Serial.print(humidity);
      Serial.print(",\"light\":");
      Serial.print(lightLevel);
      Serial.print(",\"motion\":");
      Serial.print(motionDetected);
      Serial.println("}");
    }
  }
}
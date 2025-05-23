#include <DHT.h>

#define DHTPIN 3
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int pirPin = 2;     // PIR motion sensor
const int lightPin = A1;  // Phototransistor analog pin

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(pirPin, INPUT);
}

void loop() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int lightValue = analogRead(lightPin);
  int motionDetected = digitalRead(pirPin);

  // Only send if readings are valid
  if (!isnan(temperature) && !isnan(humidity)) {
    Serial.print("TEMP:");
    Serial.print(temperature);
    Serial.print(",HUMIDITY:");
    Serial.print(humidity);
    Serial.print(",LIGHT:");
    Serial.print(lightValue);
    Serial.print(",MOTION:");
    Serial.println(motionDetected);
  } else {
    Serial.println("ERROR: Failed to read from DHT22");
  }

  delay(2000);  // Wait 2 seconds between readings
}

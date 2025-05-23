#define RELAY_PIN 8
#define LED_RED   9
#define LED_GREEN 10
#define LED_BLUE  11
#define BUZZER    12

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  // Initialize all to OFF
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_BLUE, LOW);
  digitalWrite(BUZZER, LOW);
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');

    if (command.startsWith("FAN:")) {
      if (command.endsWith("ON")) {
        digitalWrite(RELAY_PIN, HIGH);
      } else if (command.endsWith("OFF")) {
        digitalWrite(RELAY_PIN, LOW);
      }
    } else if (command.startsWith("LED:")) {
      // Format: LED:R,G,B (0 or 1)
      int r = command.charAt(4) - '0';
      int g = command.charAt(6) - '0';
      int b = command.charAt(8) - '0';
      digitalWrite(LED_RED, r);
      digitalWrite(LED_GREEN, g);
      digitalWrite(LED_BLUE, b);
    } else if (command.startsWith("BUZZER:")) {
      if (command.endsWith("ON")) {
        digitalWrite(BUZZER, HIGH);
      } else if (command.endsWith("OFF")) {
        digitalWrite(BUZZER, LOW);
      }
    }
  }
}

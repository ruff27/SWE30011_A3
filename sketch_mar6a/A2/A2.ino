// Pin definitions
#define FAN_RELAY_PIN 8
#define LED_RED_PIN 9
#define LED_GREEN_PIN 10
#define LED_BLUE_PIN 11
#define BUZZER_PIN 12

// LED states
int redValue = 0;
int greenValue = 0;
int blueValue = 0;

// Buzzer variables
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;
const unsigned long BUZZER_DURATION = 3000; // 3 seconds

void setup() {
  Serial.begin(9600);
  
  // Initialize outputs
  pinMode(FAN_RELAY_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Start with everything off
  digitalWrite(FAN_RELAY_PIN, LOW);
  setLED(0, 0, 0);
  digitalWrite(BUZZER_PIN, LOW);

  
  Serial.println("ACTUATOR_NODE_READY");
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
  
  // Handle buzzer auto-off
  if (buzzerActive && (millis() - buzzerStartTime > BUZZER_DURATION)) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerActive = false;
    Serial.println("BUZZER:OFF:TIMEOUT");
  }
}

void processCommand(String cmd) {
  if (cmd.startsWith("FAN:")) {
    String state = cmd.substring(4);
    if (state == "ON") {
      digitalWrite(FAN_RELAY_PIN, HIGH);
      Serial.println("FAN:ON:OK");
    } else if (state == "OFF") {
      digitalWrite(FAN_RELAY_PIN, LOW);
      Serial.println("FAN:OFF:OK");
    }
  }
  else if (cmd.startsWith("LED:")) {
    // Format: LED:R,G,B (values 0-255)
    String values = cmd.substring(4);
    int comma1 = values.indexOf(',');
    int comma2 = values.lastIndexOf(',');
    
    if (comma1 > 0 && comma2 > comma1) {
      int r = values.substring(0, comma1).toInt();
      int g = values.substring(comma1 + 1, comma2).toInt();
      int b = values.substring(comma2 + 1).toInt();
      
      setLED(r, g, b);
      Serial.println("LED:SET:OK");
    }
  }
  else if (cmd.startsWith("BUZZER:")) {
    String state = cmd.substring(7);
    if (state == "ON") {
      digitalWrite(BUZZER_PIN, HIGH);
      buzzerActive = true;
      buzzerStartTime = millis();
      Serial.println("BUZZER:ON:OK");
    } else if (state == "OFF") {
      digitalWrite(BUZZER_PIN, LOW);
      buzzerActive = false;
      Serial.println("BUZZER:OFF:OK");
    }
  }
  else if (cmd == "STATUS") {
    sendStatus();
  }
}

void setLED(int r, int g, int b) {
  // Constrain values to valid range
  redValue = constrain(r, 0, 255);
  greenValue = constrain(g, 0, 255);
  blueValue = constrain(b, 0, 255);
  
  // Set PWM values
  analogWrite(LED_RED_PIN, redValue);
  analogWrite(LED_GREEN_PIN, greenValue);
  analogWrite(LED_BLUE_PIN, blueValue);
}

void sendStatus() {
  Serial.print("{\"fan\":");
  Serial.print(digitalRead(FAN_RELAY_PIN));
  Serial.print(",\"led\":{\"r\":");
  Serial.print(redValue);
  Serial.print(",\"g\":");
  Serial.print(greenValue);
  Serial.print(",\"b\":");
  Serial.print(blueValue);
  Serial.print("},\"buzzer\":");
  Serial.print(buzzerActive ? 1 : 0);
  Serial.println("}");
}
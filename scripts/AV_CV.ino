

// the setup function runs once when you press reset or power the board
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == '1') {
      digitalWrite(LED_BUILTIN, HIGH);
    } else if (command == '0') {
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}

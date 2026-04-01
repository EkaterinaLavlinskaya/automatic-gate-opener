// Автоматическое управление воротами
// Пин реле: 7

const int RELAY_PIN = 7;
bool gateOpen = false;

void setup() {
  Serial.begin(9600);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);  // реле разомкнуто
  Serial.println("Arduino ready");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "OPEN" && !gateOpen) {
      digitalWrite(RELAY_PIN, LOW);   // замыкаем реле
      gateOpen = true;
      Serial.println("GATE OPEN");
      delay(3000);                    // 3 секунды
      digitalWrite(RELAY_PIN, HIGH);  // размыкаем
      gateOpen = false;
      Serial.println("GATE CLOSED");
    }
  }
}

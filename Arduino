const int shockPin = 3;

void setup() {
  pinMode(shockPin, OUTPUT);
  digitalWrite(shockPin, HIGH); // OFF (active-low)

  Serial.begin(115200);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "SHOCK_ON") {
      digitalWrite(shockPin, LOW);
    }

    else if (cmd == "SHOCK_OFF") {
      digitalWrite(shockPin, HIGH);
    }
  }
}

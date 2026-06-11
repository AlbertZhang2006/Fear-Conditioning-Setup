const int shockPin = 3;
const int cameraTriggerPin = 2;

void setup() {
  pinMode(shockPin, OUTPUT);
  digitalWrite(shockPin, HIGH); // OFF (active-low)

  pinMode(cameraTriggerPin, OUTPUT);
  digitalWrite(cameraTriggerPin, LOW);

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

    else if (cmd == "CAMERA_ON") {
      digitalWrite(cameraTriggerPin, HIGH);
    }

    else if (cmd == "CAMERA_OFF") {
      digitalWrite(cameraTriggerPin, LOW);
    }
  }
}

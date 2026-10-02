// noise_capture.ino
// Arduino sketch to collect unfiltered noise data from sensors and stream to serial/BLE

const int analogPin = A0; // Change this based on your sensor pin
const int samplingRate = 100; // Hz (adjust as needed)

void setup() {
  Serial.begin(9600);
  delay(1000);
}

void loop() {
  int rawValue = analogRead(analogPin);  // Read noisy sensor value
  unsigned long timestamp = millis();    // Optional: Timestamp

  // Output in CSV format: timestamp,rawValue
  Serial.print(timestamp);
  Serial.print(",");
  Serial.println(rawValue);

  delay(1000 / samplingRate);
}

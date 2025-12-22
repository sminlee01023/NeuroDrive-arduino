#include <Arduino.h>
#include <Wire.h>
#include <SoftwareSerial.h>

// ====== EEG (BT-986) ======
SoftwareSerial mySerial(12, 10); // RX, TX
#define BAUDRATE 57600

int generatedChecksum = 0;
byte checksum = 0;

byte payloadLength = 0;
byte payloadData[32] = {0};

byte signalquality = 0;
byte attention = 0;
byte meditation = 0;

volatile int iRxFlag = 0;

// ====== RC Car Motor ======
int motorL[2] = {3, 11};
int motorR[2] = {5, 6};

int switchPin = 9;

// ====== EEG Functions ======
byte ReadOneByte() {
  while (!mySerial.available());
  return mySerial.read();
}

void read_serial_data() {
  if (ReadOneByte() == 0xAA) {
    if (ReadOneByte() == 0xAA) {

      payloadLength = ReadOneByte();

      if (payloadLength == 0x20) {
        generatedChecksum = 0;

        for (int i = 0; i < payloadLength; i++) {
          payloadData[i] = ReadOneByte();
          generatedChecksum += payloadData[i];
        }

        checksum = ReadOneByte();
        generatedChecksum = (~generatedChecksum) & 0xff;

        // if (checksum == generatedChecksum) {
        //   iRxFlag = 1;

        signalquality = payloadData[1];
        attention     = payloadData[29];
        meditation    = payloadData[31];

        Serial.print("Attention = ");
        Serial.print(attention);
        Serial.print("    Speed = ");
        Serial.println(attention+100);

        iRxFlag = 1;
        // }
      }
    }
  }
}

// ====== CAR CONTROL ======
void carStop() {
  analogWrite(motorL[0], 0);
  analogWrite(motorL[1], 0);
  analogWrite(motorR[0], 0);
  analogWrite(motorR[1], 0);
}

void carForward(int speedVal) {
  analogWrite(motorL[0], speedVal);
  analogWrite(motorL[1], 0);

  analogWrite(motorR[0], speedVal);
  analogWrite(motorR[1], 0);
}

// ====== SETUP ======
void setup() {
  Serial.begin(9600);
  mySerial.begin(BAUDRATE);

  pinMode(switchPin, INPUT);

  for(int i=0; i<2; i++){
    pinMode(motorL[i], OUTPUT);
    pinMode(motorR[i], OUTPUT);
  }

  carStop();
}

// ====== LOOP ======
void loop() {
  // EEG data read
  if (mySerial.available()) {
    read_serial_data();
  }

  int sw = digitalRead(switchPin);

  if (sw == HIGH) {
    int speedVal = attention+100;

    carForward(speedVal);
  }
  else {
    carStop();
  }

  iRxFlag = 0;
}

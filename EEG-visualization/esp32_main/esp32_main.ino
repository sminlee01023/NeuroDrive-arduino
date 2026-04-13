#include <Arduino.h>
#include <HardwareSerial.h> 

const int rxPin = 2; // 뇌파 모듈 TX -> D2
const int txPin = 3; // 뇌파 모듈 RX -> D3 

HardwareSerial mySerial(1); 
#define EEG_BAUDRATE 57600

byte payloadData[256];

byte ReadOneByte() {
  int timeout = 0;
  while (!mySerial.available()) {
    delayMicroseconds(50);
    timeout++;
    if (timeout > 5000) return 0xFF; 
  }
  return mySerial.read();
}

void setup() {
  Serial.begin(115200); 
  mySerial.begin(EEG_BAUDRATE, SERIAL_8N1, rxPin, txPin);
}

void loop() {
  if (mySerial.available()) {
    if (ReadOneByte() == 0xAA) {
      if (ReadOneByte() == 0xAA) {
        
        byte pLength = ReadOneByte();
        if (pLength > 169) return; 

        int genChecksum = 0;
        for (int i = 0; i < pLength; i++) {
          payloadData[i] = ReadOneByte();
          genChecksum += payloadData[i];
        }
        
        byte checksum = ReadOneByte();
        genChecksum = (~genChecksum) & 0xff;

        if (checksum == genChecksum) {
          int i = 0;
          while (i < pLength) {
            byte code = payloadData[i];
            
            if (code == 0x80) { 
              byte vLength = payloadData[i+1];
              
              int rawVal = (payloadData[i+2] << 8) | payloadData[i+3];
              if (rawVal > 32767) rawVal -= 65536;
              
              Serial.println(rawVal);
              
              i += 2 + vLength;
            } else if (code >= 0x80) {
              i += 2 + payloadData[i+1];
            } else {
              i++;
            }
          }
        }
      }
    }
  }
}

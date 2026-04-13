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
  // 고속 통신을 위해 115200 유지
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
            
            // 🌟 0x80 = 원시 뇌파(Raw Data) 신호 포착! (1초에 512번 들어옴)
            if (code == 0x80) { 
              byte vLength = payloadData[i+1];
              
              // 2바이트 데이터를 10진수로 변환
              int rawVal = (payloadData[i+2] << 8) | payloadData[i+3];
              if (rawVal > 32767) rawVal -= 65536; // 음수 처리
              
              // 파이썬으로 쉴 새 없이 쏘기
              Serial.println(rawVal);
              
              i += 2 + vLength;
            } else if (code >= 0x80) {
              i += 2 + payloadData[i+1]; // 멀티 바이트 데이터 건너뛰기
            } else {
              i++; // 싱글 바이트 데이터 건너뛰기
            }
          }
        }
      }
    }
  }
}

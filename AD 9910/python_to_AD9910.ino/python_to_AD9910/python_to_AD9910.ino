const int PLL_LOCK = 7;
const int IO_UPDATE = 8;
const int IO_RESET = 9;
const int MASTER_RESET = 10;
const int SCLK = 13;
const int SDIO = 11;
const int SDO = 12;

int pllVal = 0;
char inChar = 0;
char modeByte = -1;
bool readingLine = false;
int counter = 0;
char bytearr[3];
int fullbyte = 0;
bool reading = false;
bool echo = false;



#include <SPI.h>

void setup() {
    pinMode(IO_UPDATE, OUTPUT);
    pinMode(IO_RESET, OUTPUT);
    pinMode(MASTER_RESET, OUTPUT);
    pinMode(SCLK, OUTPUT);
    pinMode(SDIO, OUTPUT);

    pinMode(PLL_LOCK, INPUT);

    Serial.begin(19200);
    
    SPI.beginTransaction(SPISettings(50000,MSBFIRST,SPI_MODE0));

    Reset_chip();
    
    //byte addr = byte(0x0E);
    //SPI.transfer(addr);
    //SPI.transfer(byte(0xFF)); //bits 63-56
    //SPI.transfer(byte(0xFF)); //bits 55-48
    //SPI.transfer(byte(0x00)); //bits 47-40
    //SPI.transfer(byte(0x00)); //bits 39-32
    //SPI.transfer(byte(0x4C)); //bits 31-24
    //SPI.transfer(byte(0x0B)); //bits 23-16
    //SPI.transfer(byte(0x78)); //bits 15-8
    //SPI.transfer(byte(0x03)); //bits 7-0
    //Update_io();

    Serial.write("DONE\n");

  //  char data = SPI.transfer(byte(135));
   // Serial.write(data);
    //char data = SPI.transfer(byte(135));
    //Serial.write(data)
    //char data = SPI.transfer(byte(135));
    //Serial.write(data)
    //char data = SPI.transfer(byte(135));
    //Serial.write(data)    
}


void loop() {
    if (Serial.available()){
        inChar = Serial.read();
        switch (inChar) {
            case 'U':{
                Update_io();
                counter = 0;
                Serial.write("U.\n");
                break;
            }
            case 'S':{
                Reset_io();
                counter = 0;
                Serial.write("S.\n");
                break;
            }
            case 'W':{
                reading = false;
                counter = 0;
                break;
            }
            case 'R':{
                reading = true;
                counter = 0;             
                break;
            }
            case 'E':{
                echo = true;
                counter = 0;
                break;
            }
            case 'P':{
                read_PLLlock();
                counter = 0;
                break;
            }
            case 13:{ //carriage return /r
                readingLine = false;
                counter = 0;
                if (reading){
                    // Do something if reading from the DDSCHIP
                    reading = false;
                }
                echo = false;
                break;
            }
            default:{
                bytearr[counter] = inChar;
                counter++;    
                if (counter >= 2){
                    fullbyte = (int) strtol(bytearr,NULL,16);
                    if (echo){
                        Serial.write(bytearr);  
                    }
                    else{
                        SPI.transfer(byte(fullbyte));
                    }
                    counter = 0;
                }
               break;
            }
        }
    }   
}

void serial_write(byte data){
  Serial.write(((data>>4) & 15) + '0');
  Serial.write((data & 15) + '0');
  Serial.write('\n');
}

void Update_io(){
    digitalWrite(IO_UPDATE, HIGH);
    delay(1);
    digitalWrite(IO_UPDATE, LOW);
}

void Reset_chip(){

    digitalWrite(MASTER_RESET, HIGH);
    delay(1);
    digitalWrite(MASTER_RESET, LOW);
    Reset_io();
    
    //Setup onedirectional communication (3 wire setup)
    byte addr = byte(0x00);
    SPI.transfer(addr);
    SPI.transfer(byte(0x40)); //bits 31-24
    SPI.transfer(byte(0x00)); //bits 23-16
    SPI.transfer(byte(0x00)); //bits 15-8
    SPI.transfer(byte(0x02)); //bits 7-0
    Update_io();
    
    Reset_io();
    addr = byte(0x02);
    SPI.transfer(addr);
    SPI.transfer(B00000011); //bits 31-24
    SPI.transfer(B00111000); //bits 23-16
    SPI.transfer(B11000001); //bits 15-8
    SPI.transfer(B11011100); //bits 7-0
    
    Update_io();


}

void Reset_io(){
    digitalWrite(IO_RESET, HIGH);
    delay(1);
    digitalWrite(IO_RESET, LOW);

}

void read_PLLlock(){
    int val = digitalRead(PLL_LOCK);
    if (val > 0){
      Serial.write("1P.\n");
    }
    else{
      Serial.write("0P.\n");
    }
}

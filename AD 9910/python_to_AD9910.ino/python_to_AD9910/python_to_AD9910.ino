const int PLL_LOCK = 7;
const int IO_UPDATE = 8;
const int IO_RESET = 9;
const int MASTER_RESET = 10;
const int SCLK = 10;
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
    pinMode(SS, OUTPUT);

    pinMode(PLL_LOCK, INPUT);
    pinMode(SDO, INPUT);

    SPI.beginTransaction(SPISettings(16000000,MSBFIRST,SPI_MODE0));
    
    //Setup onedirectional communication (3 wire setup)
    byte addr = byte(0);
    SPI.transfer(addr);
    SPI.transfer(byte(0)); //bits 31-24
    SPI.transfer(byte(0)); //bits 23-16
    SPI.transfer(byte(0)); //bits 15-8
    SPI.transfer(byte(2)); //bits 7-0

    Serial.begin(9600);
}


void loop() {
    if (Serial.available()){
        inChar = Serial.read();
        switch (inChar) {
            case 'U':{
                UPDATE();
                counter = 0;
                break;
            }
            case 'S':{
                RESET();
                counter = 0;
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
                if (counter >= 1){
                    fullbyte = (int) strtol(bytearr,NULL,16);
                    if (echo){
                        Serial.write(fullbyte);  
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


void writeToChip(byte addr, byte data[],int length){
    SPI.transfer(addr);
    for (int i = 0; i < length; i++){
        SPI.transfer(data[i]);
    }
}

void UPDATE(){
    digitalWrite(IO_UPDATE, HIGH);
    delay(1);
    digitalWrite(IO_UPDATE, LOW);
}

void RESET(){
    digitalWrite(IO_RESET, HIGH);
    delay(1);
    digitalWrite(IO_RESET, LOW);
}

void read_PLLlock(){
    int val = digitalRead(PLL_LOCK)
    Serial.write(val)
    Serial.write('\n')
}

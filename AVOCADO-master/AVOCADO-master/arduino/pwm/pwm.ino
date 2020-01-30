#include <Wire.h>
#include "TimerThree.h"
  
int count = 0;
int s_out = 5;
int m_out = 3;
int s_in = 4;
int dir = 150;
int duty = 0;
int comBuf[10];
float freq;
int jetson;
int value;
int samples = 10;
long timeout = 40000;
#define FREQMEASURE_BUFFER_LEN 12
static volatile uint32_t buffer_value[FREQMEASURE_BUFFER_LEN];
static volatile uint8_t buffer_head;
static volatile uint8_t buffer_tail;

void setup() 
{
    pinMode(s_out, OUTPUT);
    pinMode(m_out, OUTPUT);
    pinMode(s_in, INPUT);
    Timer3.initialize(10000);         // initialize timer1, and set a 1/2 second period
    Wire.begin(8);
    Wire.onReceive(receiveEvent);
    Wire.onRequest(requestEvent);
    Serial.begin(115200);
    Serial.print("inititialized");
    //analogWrite(m_out, 0);
}

void loop() 
{
  //dir = 102;
  // value is % duty cycle out of 1024
  // look in receiveEvent for scaling calcs
   Timer3.pwm(s_out, dir);
   //Serial.print("\nDir = ");
   //Serial.print(dir);
   Timer3.pwm(m_out, duty);
   read_freq();
}

void read_freq()
{
  int i = 0;
  unsigned long period = 0;
  unsigned long count = 0;
  long total = 0;
  for(i = 0; i < samples; i++)
  {
    total += pulseIn(s_in, LOW, timeout);
  }
  period = total / samples;
  if(period != 0)
    freq = 1000000 / period;
  else
    freq = 0;
  jetson = (int)freq;
  jetson = jetson / 2;
  //Serial.print("\nfreq = ");
  //Serial.print(freq);
}

void requestEvent()
{
  Wire.write(jetson); 
}

void receiveEvent(int howMany) {
  while(Wire.available())
  {
    // reading array from jetson
    for(int i = 0; i < 10; i++)
    {
      comBuf[i] = Wire.read();
    }
  }
  //Serial.print("\nDir = ");
  //Serial.print(comBuf[2]);
  // Jacob look here
  // scale from / 1000 to / 1024
  dir = comBuf[2] * 1.024;
  dir = (int)dir;
  // scale from / 256 to / 1024
  duty = comBuf[3]; 
  
  //Serial.print("\nDuty = ");
  //Serial.print(duty);

  //delayMicroseconds(500); 
}

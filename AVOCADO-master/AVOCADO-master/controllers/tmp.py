# -*- coding: utf-8 -*-
## @file main.py
#  @package Encoder
#  @authors Jacob Loh, Josh Neiman

import pyb
import utime
import Encoder
import Controller
import Motor

## Contains code for main to test Encoder class functionality.
def main():
    kp = 50
    ki = 5
    controller1 = Controller.Controller(0, kp, ki)
    encoder1 = Encoder.Encoder("B")

    motor1 = Motor.MotorDriver()
    encoderTicks = 2000;

    setpt = 0
    output = []
    
    for t in range(0, 1.5*10000):
        pos = encoder1.read()
        posRad = 2*pos*3.1415/encoderTicks #convert from 
        print(str(t) + "," + str(posRad))

        pwm = controller1.get_response(posRad)
        motor1.set_duty_cycle(pwm)
        utime.sleep_ms(10)
        if t == 0.5*100:
            setpt = 3.14
            controller1.set_setpoint(setpt)

    print("Step done")

        
if __name__ == '__main__':
    main() # run main function





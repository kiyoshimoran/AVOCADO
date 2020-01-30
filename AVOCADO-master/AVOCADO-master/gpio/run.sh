#!/bin/bash

g++ pwm.cpp  -o pwm
g++ steering.cpp jetsonGPIO.cpp -o steering
g++ motor.cpp jetsonGPIO.cpp -o motor

./pwm

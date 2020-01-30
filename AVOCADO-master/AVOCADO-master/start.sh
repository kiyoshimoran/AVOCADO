#!/bin/bash
clear
g++ main.cpp -o main
g++ ./gpio/i2c.cpp -li2c -o ./gpio/i2c
g++ ./io/parser.cpp -o ./io/parser
g++ ./controllers/laneDetectionController.cpp -o ./controllers/laneDetectionController
g++ ./controllers/platooningController.cpp -o ./controllers/platooningController
g++ ./gpio/Motor.cpp ./gpio/jetsonGPIO.cpp -o ./gpio/Motor
#g++ ./gpio/i2c.cpp ./gpio/JHLEDBackpack.cpp -o ./gpio/i2c
#g++ ./gpio/steering.cpp ./gpio/jetsonGPIO.cpp -o ./gpio/steering
./main

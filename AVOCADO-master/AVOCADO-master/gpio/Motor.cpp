#include <stdio.h>
#include <unistd.h>
#include <iostream>
#include <sys/poll.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <stdlib.h>

//TODO Change to be able to modify speed while braking

#include "jetsonGPIO.h"
#include "../include/pipes/object_detection_to_motor.h"
#include "../include/pipes/lane_detection_response.h"
#include "../include/pipes/camera_pipes.h"
#include "../include/pipes/platoon_pipes.h"
#include "../include/pipes/parser_pipes.h"
#include "../include/pipes/communication.h"

//#define scale(x) ((x / 2) + 1) * 1000
#define freq 10000
#define NUM_BRAKES 4
#define STDIN 0
#define LD 1
#define OD 2
#define PLATOON 3

// Global Variables
int crawl = 9 * 4;
int slow = 12 * 4;
int medium = 14 * 4;
int fast = 16 * 4;
int ludicrous = 20 * 4;

using namespace std;

void printMinSpeedBuf(int *minSpeed);
int getMinVal(int *minSpeed, int length);

int main(int argc, char ** argv) {
    int dir, rev, up_time, down_time, i, ret, PPfd, fd, Platoonfd, platoonDuty, bytesRead, parserfd, platoonfd, minSpeedSent, currSpeed, retSpeed, motor_to_comm;
    char c;
    struct pollfd fds, PPfds, Platoonfds, parserfds, platoonfds;

    //char object_detection_to_motor[] = OBJECT_DETECTION_TO_MOTOR;
    int object_detection_fd;

    int driveStatus[4] = {0, 1, 1, 1}; // {user, LD, OD, Platoon}
    int minSpeed[4] = {medium, ludicrous, ludicrous, ludicrous};
    int drive = 0;

    char tmpStr[] = "/tmp/object_detection_to_motor";

    char colePipe[] = "/tmp/colePipe";
    if ((Platoonfd = open(colePipe, O_RDONLY)) == -1) { // out resp
        perror("Motor: Failed to open PLATOONING_PID_TO_MOTOR pipe");
        exit(-1);
    }
    if ((fd = open(LANE_DETECTION_RESPONSE, O_WRONLY)) == -1) { // out resp
        perror("Motor: Failed to open LANE_DETECTION_RESPONSE pipe");
        exit(-1);
    }
    if ((motor_to_comm = open(MOTOR_TO_COMM, O_WRONLY)) == -1) { // out resp
        perror("Motor: Failed to open MOTOR_TO_COMM pipe");
        exit(-1);
    }
    if ((parserfd = open(PARSER_TO_MOTOR, O_RDONLY)) == -1) { // out resp
        perror("Motor: Failed to open PARSER_TO_MOTOR pipe");
        exit(-1);
    }
    if ((platoonfd = open(PLATOONING_TO_MOTOR, O_RDONLY)) == -1) { // out resp
        perror("Motor: Failed to open PLATOONING_TO_MOTOR pipe");
        exit(-1);
    }
    if ((PPfd = open(PP_TO_MOTOR, O_RDONLY)) == -1) { // out resp
        perror("Motor: Failed to open PP_TO_MOTOR pipe");
        exit(-1);
    }

    fds.fd = 0;
    PPfds.fd = PPfd;
    Platoonfds.fd = Platoonfd;
    parserfds.fd = parserfd;
    platoonfds.fd = platoonfd;

    fds.events = POLLIN;
    PPfds.events = POLLIN;
    Platoonfds.events = POLLIN;
    parserfds.events = POLLIN;
    platoonfds.events = POLLIN;

    jetsonTX2GPIONumber motor = gpio395;
    jetsonTX2GPIONumber enabe = gpio298; //not sure about reading input yet
    jetsonTX2GPIONumber direction = gpio388; // set high to reverse car direction
    //clear pins
    //gpioUnexport(steering);
    //gpioUnexport(motor);
    gpioUnexport(enabe);
    gpioUnexport(direction);
    //set pins
    gpioExport(direction);
    gpioExport(motor);
    gpioExport(enabe);
    gpioSetDirection(motor, outputPin);
    gpioSetDirection(enabe, outputPin);
    gpioSetDirection(direction, outputPin);
    gpioSetValue(enabe, off);
    gpioSetValue(direction, off);
    usleep(1000);
    //gpioSetValue(enabe, on);
    dir = 255;
    int speed = 30;
    fprintf(stderr, "Motor speed (us on): %i\n", speed);
    int j;


    /*
    fprintf(stderr, "BEFORE OPENING PIPE\n");
    if ((object_detection_fd = open(OBJECT_DETECTION_TO_MOTOR, O_RDONLY)) == -1) { // out resp
        perror("main: Failed to open OBJECT_DETECTION_TO_MOTOR pipe");
        //exit(-1);
    }
    fprintf(stderr, "AFTER OPENING PIPE\n");
    */

    char stdinBuf[10];
    fprintf(stderr, "Drive (d), Brake (b), and Quit (q)\n");
    fprintf(stderr, "Ludicrous (l), Fast (f), Medium (m), Slow (s), Crawl (c)\n");
    fprintf(stderr, "Will begin with a medium (%i) speed.\n", medium);
    write(fd, &medium, sizeof (int));
    minSpeedSent = medium;
    currSpeed = -1;
    printMinSpeedBuf(minSpeed);
    //write(motor_to_comm, &currSpeed, sizeof (int));
    printf("Starting Motor.cpp\n");
    while (1) {
        // Read from parser pipe
        ret = poll(&parserfds, 1, 0); // struct, numFDs, timeout
        if(ret == 1) {
            memset(stdinBuf, 0, 10); // TODO Put memsets before all the stdin reads!!!
            read(parserfds.fd, stdinBuf, 10); 
            if (stdinBuf[0] == 'q') {
                driveStatus[STDIN] = -1;
            }
            else if (stdinBuf[0] == 'b') {
                driveStatus[STDIN] = 0;
            }
            /*
            else if (stdinBuf[0] == 'r') { // this one doesn't work. Bad gearing?
                fprintf(stderr, "Reverse\n");
                gpioSetValue(direction, on);
                gpioSetValue(enabe, off);
                gpioSetValue(enabe, on);
            }
            */
            else if (stdinBuf[0] == 'd') { // drive
                driveStatus[STDIN] = 1;
            }
            else if (stdinBuf[0] == 'l') { // drive
                //fprintf(stderr, "stdin: Go ludicrous (%i)!\n", ludicrous);
                //write(fd, &ludicrous, sizeof (int));
                minSpeed[STDIN] = ludicrous;
            }
            else if (stdinBuf[0] == 'f') { // drive
                //fprintf(stderr, "stdin: Go fast (%i)!\n", fast);
                //write(fd, &fast, sizeof (int));
                minSpeed[STDIN] = fast;
            }
            else if (stdinBuf[0] == 'm') { // drive
                //fprintf(stderr, "stdin: Go medium (%i)!\n", medium);
                //write(fd, &medium, sizeof (int));
                minSpeed[STDIN] = medium;
            }
            else if (stdinBuf[0] == 's') { // drive
                ////fprintf(stderr, "stdin: Go slow (%i)!\n", slow);
                //write(fd, &slow, sizeof (int));
                minSpeed[STDIN] = slow;
            }
            else if (stdinBuf[0] == 'c') { // drive
                //fprintf(stderr, "stdin: Go crawl (%i)!\n", crawl);
                //write(fd, &crawl, sizeof (int));
                minSpeed[STDIN] = crawl;
            }
            //else if (stdinBuf[0] == 'o') {
            memset(stdinBuf, 0, 10);
        }
        // Read object description
        // TODO Manage broken OD pipe
        ret = poll(&PPfds, 1, 0); // struct, numFDs, timeout
        if(ret == 1) {
            read(PPfds.fd, stdinBuf, 10); 
            //fprintf(stderr, "I received: %s\n", stdinBuf);
            if (stdinBuf[0] == 'd') {
                fprintf(stderr, "Received OD drive\n");
                driveStatus[2] = 1;
            }
            else if (stdinBuf[0] == 'b') {
                fprintf(stderr, "Received OD brake\n");
                driveStatus[2] = 0;
            }
            else if (stdinBuf[0] == 'l') {
                fprintf(stderr, "Received OD ludicrous\n");
                //write(fd, &ludicrous, sizeof (int));
                minSpeed[OD] = ludicrous;
            }
            else if (stdinBuf[0] == 's') {
                fprintf(stderr, "Received OD slow\n");
                //write(fd, &slow, sizeof (int));
                minSpeed[OD] = slow;
            }
            else if (stdinBuf[0] == 'q') {
                driveStatus[2] = -1;
            }
            memset(stdinBuf, 0, 10);
        }
        // Read from platoon.py, user commands to form/break platoon
        ret = poll(&platoonfds, 1, 0); // struct, numFDs, timeout
        if(ret == 1) {
            // Only enter here on p (form platoon) or n (break platoon)
            read(platoonfds.fd, stdinBuf, 10); 
            if (stdinBuf[0] == 'p') { // forming platoon
                minSpeed[STDIN] = ludicrous; // chase at fast speed
            }
            if (stdinBuf[0] == 'n') { // breaking platoon
                minSpeed[STDIN] = slow;
                minSpeed[PLATOON] = ludicrous;
                while ((poll(&Platoonfds, 1, 0)) == 1) { // empty buff in case still sending platoon values
                    // drain pipe at formation/break-ation of platoon
                    bytesRead = read(Platoonfds.fd, &stdinBuf, sizeof (int)); 
                }
            }
            memset(stdinBuf, 0, 10);
        }
        ret = poll(&Platoonfds, 1, 0); // struct, numFDs, timeout
        // Actually reading platoon response values
        if (ret == 1) {
            bytesRead = read(Platoonfds.fd, &stdinBuf, sizeof (int)); 
            while ((poll(&Platoonfds, 1, 0)) == 1) {
                bytesRead = read(Platoonfds.fd, &stdinBuf, sizeof (int)); 
            }
            //fprintf(stderr, "Motor: %x\n", *((int *) stdinBuf));
            //platoonDuty = atoi(stdinBuf);
            platoonDuty = *(int *) stdinBuf;
            if (platoonDuty == 0) {
                driveStatus[3] = 0;
            }
            else {
                driveStatus[3] = 1;
                //write(fd, &platoonDuty, sizeof (int));
                minSpeed[PLATOON] = platoonDuty;
            }
            memset(stdinBuf, 0, 10);
        }
        if (driveStatus[0] == -1 || driveStatus[1] == -1 || driveStatus[2] == -1 || driveStatus[3] == -1) {
            gpioSetValue(direction, on); // throw on reverse briefly
            usleep(500000);
            gpioSetValue(direction, off); // turn off reverse to prevent rollback
            // TODO Put platoon braking send in here
            break;
        }
        else if (driveStatus[0] == 0 || driveStatus[1] == 0 || driveStatus[2] == 0 || driveStatus[3] == 0) {
            gpioSetValue(direction, on); // throw on reverse briefly
            usleep(100000);
            gpioSetValue(enabe, off); // enable off to stop rollback
            retSpeed = 0;
            if (retSpeed != currSpeed) {
                currSpeed = retSpeed;
                printf("Running at: %i\n", currSpeed);
                write(motor_to_comm, &currSpeed, sizeof (int));
            }
        }
        else {
            gpioSetValue(direction, off);
            gpioSetValue(enabe, off);
            gpioSetValue(enabe, on);
            retSpeed = getMinVal(minSpeed, 4);
            if (retSpeed != currSpeed) {
                write(fd, &retSpeed, sizeof (int));
                currSpeed = retSpeed;
                //printMinSpeedBuf(minSpeed);
                //printf("Running at: %i\n", currSpeed);
                write(motor_to_comm, &currSpeed, sizeof (int));
            }
        }

        gpioSetValue(motor, on);
        usleep(speed);
        gpioSetValue(motor, off);
        usleep(1000 - speed);
        //TODO read direction
    }
    gpioSetValue(motor, off);
    gpioSetValue(enabe, off);
    gpioUnexport(motor);
    fprintf(stderr, "MOTOR OFF\n");
    //gpioUnexport(enabe);
    return 0;
}

void printMinSpeedBuf(int *minSpeed) {
    fprintf(stderr, "[%i, %i, %i, %i]\n", minSpeed[0], minSpeed[1], minSpeed[2], minSpeed[3]);
}

int getMinVal(int *minSpeed, int length) {
    int minIndex = 0;
    int minValue = minSpeed[minIndex];
    for (int i=0; i<length; i++) {
        if (minSpeed[i] < minValue) {
            minValue = minSpeed[i];
            minIndex = i;
        }
    }
    return minValue;
}

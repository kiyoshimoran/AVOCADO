#include <stdio.h>
#include <poll.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/time.h>
#include <string.h>

#include "../include/pipes/platoon_pipes.h"
#include "../include/pipes/communication.h"

#define INIT_PREV 1.23456789 // FIX THIS

int main() {
    // Gains and limits
    float positionInfluence = 0.1;
    float freqInfluence = 0.03;
    float kp = 0.8;
    float ki = 0.0;
    float kd = 0.05;
    int heightMax = 215;
    float heightSetpoint = 115.0;
    int dutyMin = 7 * 4;
    int dutyMax = 18 * 4;
    int otherCar = 0;
    char getting_comm_to_pid[] = "/tmp/getting_comm_to_pid";
    // End of gains and limits

    int fdPlatoonVel, fdPlatoonDist, fdMotor, pollReturn, bytesRead, fdCommDutyMin, fdCommDutyMax, fdCommToPlatooningPid, freqFD, otherFreqFD;
    struct pollfd velFds, distFds, motorFds, commDutyMinFds, commDutyMaxFds, commToPlatooningPidFds, freqFds, otherFreqFds;
    char buf[20];

    // TODO (wishlist): Understand why COMM_TO_PLATOONING_PID pipe was failing
    //if ((fdCommToPlatooningPid = open(COMM_TO_PLATOONING_PID, O_RDONLY)) == -1) { // out resp
    char colePipe[] = "/tmp/colePipe";
    if ((fdMotor = open(colePipe, O_WRONLY)) == -1) { // out resp
        perror("Platoon Pid: Failed to open PLATOONING_PID_TO_MOTOR pipe");
        exit(-1);
    }
    if ((freqFD = open(FREQ_TO_CONTROLLER, O_RDONLY)) == -1) { // out resp
        perror("Platoon Pid: Failed to open FREQ_TO_CONTROLLER pipe");
        exit(-1);
    }
    if ((fdCommToPlatooningPid = open(getting_comm_to_pid, O_RDONLY)) == -1) { // out resp
        perror("Platoon Pid: Failed to open COMM_TO_PLATOONING_PID pipe");
        exit(-1);
    }
    if ((otherFreqFD = open(OTHER_FREQ_TO_PID, O_RDONLY)) == -1) { // out resp
        perror("Platoon Pid: Failed to open OTHER_FREQ_TO_PID pipe");
        exit(-1);
    }
    if ((fdPlatoonDist = open(PLATOONING_DIST_PIPE, O_RDONLY)) == -1) { // out resp
        perror("Platoon Pid: Failed to open PLATOONING_DIST_PIPE pipe");
        exit(-1);
    }
    if ((fdPlatoonVel = open(PLATOONING_VEL_PIPE, O_RDONLY)) == -1) { // out resp
        perror("Platoon Pid: Failed to open PLATOONING_VEL_PIPE pipe");
        exit(-1);
    }
    velFds.fd = fdPlatoonVel;
    distFds.fd = fdPlatoonDist;
    commDutyMinFds.fd = fdCommDutyMin;
    commDutyMaxFds.fd = fdCommDutyMax;
    commToPlatooningPidFds.fd = fdCommToPlatooningPid;
    freqFds.fd = freqFD;
    otherFreqFds.fd = otherFreqFD;


    velFds.events = POLLIN;
    distFds.events = POLLIN;
    commDutyMinFds.events = POLLIN;
    commDutyMaxFds.events = POLLIN;
    commToPlatooningPidFds.events = POLLIN;
    freqFds.events = POLLIN;
    otherFreqFds.events = POLLIN;

    int velSetpt, distSetpt;
    int ourFreq = 0;
    int otherFreq = 0;
    int freqError = 0;
    /*
    fprintf(stderr, "Platooning: kp: %f\n", kp);
    fprintf(stderr, "Platooning: ki: %f\n", ki);
    fprintf(stderr, "Platooning: kd: %f\n", kd);
    */
    float prev = INIT_PREV; // FIX THISSSSSSSSSSSSSSSSSSSSSSSSSSSSSS
    struct timeval previous_time, current_time;
    //ki = 0;
    float kp_response = 0.0;
    float ki_response = 0.0;
    float kd_response = 0.0;
    float offset = 0.0;
    int timeout = 0; // number of ms until timeout
    float position = 0.0;
    float error;
    float total_response_f;
    int total_response_i;
    char total_response_c;
    float integral = 0;
    size_t numBytes = sizeof (int);
    int write_return;
    float time_delta, pidIn;
    gettimeofday(&previous_time, NULL);
    gettimeofday(&current_time, NULL);
    printf("Starting platooningController.cpp\n");
    while (1) {
        /*
        pollReturn = poll(&commDutyMinFds, 1, timeout); // check for comm val
        if (pollReturn > 0) {
            read(fdCommDutyMin, buf, 10+numBytes);                                      // why 10+? Fix this!
            printf("TRIGGERED!***************************************8\n");
            dutyMin = atoi(buf);
        }
        pollReturn = poll(&commDutyMaxFds, 1, timeout); // check for comm val
        if (pollReturn > 0) {
            read(fdCommDutyMax, buf, 10+numBytes);                                      // why 10+? Fix this!
            dutyMax = atoi(buf);
        }
        */
        pollReturn = poll(&otherFreqFds, 1, timeout); // check for freq val
        if (pollReturn > 0) {
            bytesRead = read(otherFreqFds.fd, &buf, sizeof (int));
            otherFreq = atoi(buf);
            memset(buf, 0, 10); // TODO Put memsets before all the stdin reads!!!
        }
        pollReturn = poll(&freqFds, 1, timeout); // check for freq val
        if (pollReturn > 0) {
            bytesRead = read(freqFds.fd, &ourFreq, sizeof (int));                           // why 10+? Fix this!
        }
        pollReturn = poll(&commToPlatooningPidFds, 1, timeout); // check for comm val
        /*
        read(fdCommToPlatooningPid, buf, 10+numBytes);                           // why 10+? Fix this!
        printf("Controller read: %s\n", buf);
        pollReturn = 0;
        */
        if (pollReturn > 0) {
            bytesRead = read(fdCommToPlatooningPid, buf, 10+numBytes);                           // why 10+? Fix this!
            //printf("=============\n");
            //printf("Bytes read: %i\n", bytesRead);
            //printf("Controller read: %s\n", buf);
            otherCar = atoi(buf);
            //printf("Received %i from the other car\n", otherCar);
            if (otherCar == 0) {
                dutyMin = 0;
                dutyMax = 0;
            }
            else {
                dutyMin = otherCar - 8;
                dutyMax = otherCar + 8;
            }
            memset(buf, 0, 10); // TODO Put memsets before all the stdin reads!!!
        }
        pollReturn = poll(&velFds, 1, timeout); // check for vel value
        if (pollReturn > 0) {
            read(fdPlatoonVel, buf, 10+numBytes);                                      // why 10+? Fix this!
            velSetpt = atoi(buf);
            pollReturn = poll(&distFds, 1, timeout); // check for dist value
            if (pollReturn > 0) {
                bytesRead = read(fdPlatoonDist, buf, 10+numBytes);                                      // why 10+? Fix this!
                distSetpt = atoi(buf);

                if (prev == INIT_PREV) {
                    prev = pidIn;
                }

                previous_time = current_time;
                gettimeofday(&current_time, NULL);
                if (prev == INIT_PREV) {
                    prev = pidIn;
                }
                time_delta = (float) (current_time.tv_usec - previous_time.tv_usec) / 1000000 +
                    (float) (current_time.tv_sec - previous_time.tv_sec);

                freqError = otherFreq - ourFreq;
                //printf("Error is: %i\n", freqError);
                //pidIn = freqInfluence * ((float) freqError);
                pidIn = (positionInfluence * (heightSetpoint - ((float) distSetpt))) + 
                        (freqInfluence * ((float) freqError));

                integral += pidIn;
                kp_response = kp * pidIn;
                ki_response = 0.0; //ki * integral;
                kd_response = 0.0; //kd * ((pidIn - prev) / time_delta);
                prev = pidIn;
                //ki_response = ki * integral;
                //kd_response = kd * ((setpt - prev) / time_delta);
                //prev = setpt;
                total_response_f = (kp_response + ki_response + kd_response + offset + otherCar + 1); // 1 is to compensate for different vehicle speeds
                total_response_i = (int) total_response_f;
                /*
                if (total_response_i > dutyMax) {
                    total_response_i = dutyMax;
                }
                else if (total_response_i < dutyMin) {
                    total_response_i = dutyMin;
                }
                */
                /*
                if (distSetpt > heightMax) { // too close
                    //fprintf(stderr, "Braking!   ");
                    total_response_i = 0;
                }
                */
                //fprintf(stderr, "%i\n", total_response_i);
                /*
                // Too close!
                // TODO Figure out how to brake when close without braking on turns
                if (distSetpt > 160) { // && velSetpt < -15) {
                    fprintf(stderr, "Braking (with vel)!   ");
                    total_response_i = 0;
                }
                */
                //fprintf(stderr, "Controller: %i\n",  total_response_i);
                //fprintf(stderr, "%i    %i     %i\n", distSetpt, velSetpt, total_response_i);
                //printf("Duty min: %i    Duty max: %i\n", dutyMin, dutyMax);
                if (otherCar == 0) {
                    write_return = write(fdMotor, &otherCar, sizeof (int));
                }
                else if (otherFreq == 0) {
                    write_return = write(fdMotor, &otherFreq, sizeof (int));
                }
                else {
                    write_return = write(fdMotor, &total_response_i, sizeof (int));
                }
            }
            else {
                // we timed out on dist read
            }
        }
        else {
            // we timed out on vel read
        }
    }
    return 0;
}






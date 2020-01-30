


#include <stdio.h>
#include <poll.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/time.h>

#include "../include/pipes/lane_detection_response.h"
//#include <sys/wait.h>

#define INIT_PREV 1.23456789 // FIX THIS

int main() {
    int setpt;
    float kp = 24.0 / 300.0; // 45.0 / 300.0; // 45.0 / 300.0; // 67 kp was good, no ki or ki=0.0025 is decent
    float ki = 0.0;//.5 / 300.0; //0.013;
    float kd = 2.8 / 300.0;        // 10.0 / 300.0; //0.012;
    float position = 550.0;
    //fprintf(stderr, "kp: %f\n", kp);
    //fprintf(stderr, "ki: %f\n", ki);
    //fprintf(stderr, "kd: %f\n", kd);
    float prev = INIT_PREV; // FIX THISSSSSSSSSSSSSSSSSSSSSSSSSSSSSS
    struct timeval previous_time, current_time;
    //ki = 0;
    float kp_response = 0;
    float ki_response = 0;
    float kd_response = 0;
    float offset = 155.0;
    int numFds = 1;
    struct pollfd myPollfds[numFds];
    myPollfds[0].fd = 0;
    myPollfds[0].events = POLLIN;
    int timeout = 1000; // number of ms until timeout
    int pollReturn;
    char buf[20], ppbuf[20];
    float error;
    float total_response_f;
    float integral = 0;
    int total_response_i;
    size_t numBytes = sizeof (int);
    int fd, ppfd;
    int write_return;
    float time_delta;
    if ((fd = open(LANE_DETECTION_RESPONSE, O_WRONLY)) == -1) { // out resp
        perror("main: Failed to open LANE_DETECTION_RESPONSE pipe");
        exit(-1);
    }
    if ((ppfd = open("/tmp/pp_to_LD_controller", O_RDONLY)) == -1) { // out resp
        perror("main: Failed to open pp_to_LD_controller pipe");
        exit(-1);
    }
    gettimeofday(&previous_time, NULL);
    gettimeofday(&current_time, NULL);
    printf("Starting laneDetectionController.cpp\n");
    while (1) {
        pollReturn = poll(myPollfds, numFds, timeout);
        if (pollReturn > 0) {
		read(0, buf, 10+numBytes);                                      // why 10+? Fix this!
            setpt = atoi(buf);
		//fprintf(stderr, "CR: %i\n", setpt);
            error = setpt - position; // setpt is middle of car path, position is middle of the road
            //fprintf(stderr, "ERROR IS: %f\n", error);
            
            previous_time = current_time;
            gettimeofday(&current_time, NULL);
            if (prev == INIT_PREV) {
                prev = setpt;
            }
            time_delta = (float) (current_time.tv_usec - previous_time.tv_usec) / 1000000 +
                (float) (current_time.tv_sec - previous_time.tv_sec);
            integral += error;


            //fprintf(stderr, "Error is: %f\n", error);
            /*
            if (error > 200) {
                kd = 15.0 / 300.0;
                //fprintf(stderr, "ON   ");
            }
            else {
                kd = 0.0 / 300.;
                //fprintf(stderr, "OFF  ");
            }
            if (error > 160) {
                kp = 85.0 / 300.0;
            }
            else {
                kp = 45.0 / 300.0;
            }
            */


            
            kp_response = kp * error;
            ki_response = ki * integral;
            kd_response = kd * ((setpt - prev) / time_delta);
            prev = setpt;
            total_response_f = kp_response + ki_response + kd_response + offset;
            total_response_i = (int) total_response_f;
            if (total_response_i > 255) {
                total_response_i = 255;
            }
            else if (total_response_i < 100) {
                total_response_i = 100;
            }
            //fprintf(stderr, "Total Response: %i\n", total_response_i);
            //fprintf(stderr, "\n Here: %i\n", total_response_i);
            write_return = write(fd, &total_response_i, sizeof (int));
            //fprintf(stderr, "write_return: %i\n", write_return);
            //printf("%i", total_response_i);
        }
        else if (pollReturn == -1) {
            perror("laneDetectionController: pollReturn");
            exit(-1);
        }
    }
    return 0;
}





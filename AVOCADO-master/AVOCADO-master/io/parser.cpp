#include <sys/poll.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>

#include "../include/pipes/parser_pipes.h"
#include "../include/pipes/communication.h"

int main(int argc, char ** argv) {
    struct pollfd fds;
    int ret, write_return, motorfd, platoonfd, lane_change_fd, parser_to_camera_fd, parser_to_main_fd;
    char stdinBuf[10];
    char motorString[] = "bdlfmsc"; // characters to pass to motor
    char platoonString[] = "np"; // characters to pass to platoon
    char laneChangeString[] = "gh"; // characters for lane changes
    char quitString[] = "qQ"; // quit character
    char lane_change[] = "/tmp/lane_change";
    char parser_to_camera[] = "/tmp/parser_to_camera";
    char parser_to_main[] = "/tmp/parser_to_main";

    fds.fd = 0;
    fds.events = POLLIN;
    // NOTE Add pipes in alphabetical order
    if ((lane_change_fd = open(lane_change, O_WRONLY)) == -1) { // out resp
        perror("Parser: Failed to open lane_change pipe");
        exit(-1);
    }
    if ((parser_to_camera_fd = open(parser_to_camera, O_WRONLY)) == -1) { // out resp
        perror("Parser: Failed to open parser_to_camera pipe");
        exit(-1);
    }
    if ((parser_to_main_fd = open(parser_to_main, O_WRONLY)) == -1) { // out resp
        perror("Parser: Failed to open parser_to_main pipe");
        exit(-1);
    }
    if ((motorfd = open(PARSER_TO_MOTOR, O_WRONLY)) == -1) { // out resp
        perror("Parser: Failed to open PARSER_TO_MOTOR pipe");
        exit(-1);
    }
    if ((platoonfd = open(PARSER_TO_PLATOON, O_WRONLY)) == -1) { // out resp
        perror("Parser: Failed to open PARSER_TO_PLATOON pipe");
        exit(-1);
    }
    
    printf("Starting Parser.cpp\n");
    while (1) {
        ret = poll(&fds, 1, 0); // struct, numFDs, timeout // TODO change timeout (make sure not an issue to change)
        if(ret == 1) {
            read(fds.fd, stdinBuf, 10); 
            if (strchr(motorString, stdinBuf[0])) {
                write_return = write(motorfd, &stdinBuf, sizeof (char));
            }
            else if (strchr(platoonString, stdinBuf[0])) {
                write_return = write(platoonfd, &stdinBuf, sizeof (char));
            }
            else if (strchr(laneChangeString, stdinBuf[0])) {
                write_return = write(lane_change_fd, &stdinBuf, sizeof (char));
            }
            else if (strchr(quitString, stdinBuf[0])) {
		stdinBuf[1] = 'b';
                write_return = write(motorfd, &stdinBuf[1], sizeof (char)); // stop motor
		printf("\n");
                write_return = write(parser_to_camera_fd, &stdinBuf, sizeof (char)); // send quit to camera
		sleep(1);
                write_return = write(parser_to_main_fd, &stdinBuf, sizeof (char)); // send quit to main
            }
            else {
                printf("Invalid character\n");
            }
            memset(stdinBuf, 0, 10);
        }
    }
    while (1); // wait to be killed
}






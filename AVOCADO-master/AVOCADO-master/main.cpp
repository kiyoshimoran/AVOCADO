#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <signal.h>

#include "include/pipes/parser_pipes.h"
#include "include/pipes/lane_detection_position.h"
#include "include/pipes/lane_detection_response.h"
#include "include/pipes/camera_pipes.h"
#include "include/pipes/object_detection_to_motor.h"
#include "include/pipes/platoon_pipes.h"
#include "include/pipes/communication.h"

#define LANE_KEEPING 1
#define MOTOR 1

int startParser(pid_t *pids, int *subProcesses);
int startPlatooning(pid_t *pids, int *subProcesses);
int startLaneKeeping(pid_t *pids, int *subProcesses);
int startMotor(pid_t *pids, int *subProcesses);
int makeFifo(char *fifopath);
void printStartUpMessages();

int main() {
    int wait_status = 0;
    int subProcesses = 0;
    int processesReturned;
    int parser_to_main_fd;
    struct pollfd parser_to_main_fds[1];
    char buf[10];
    pid_t pids[20];

    char camera_to_LD[] = CAMERA_TO_LD;
    char camera_to_OD[] = CAMERA_TO_OD;
    char camera_to_Platooning[] = CAMERA_TO_PLATOONING;
    char camera_to_recorder[] = "/tmp/camera_to_recorder";
    char colePipe[] = "/tmp/colePipe";
    char comm_to_lane_change[] = "/tmp/comm_to_lane_change";
    char comm_to_platooning_pid[] = COMM_TO_PLATOONING_PID;
    char freq_to_comm[] = FREQ_TO_COMM;
    char freq_to_controller[] = FREQ_TO_CONTROLLER;
    char getting_comm_to_pid[] = "/tmp/getting_comm_to_pid";
    char lane_change[] = "/tmp/lane_change";
    char lane_change_comm[] = "/tmp/lane_change_to_comm";
    char lane_detection_position[] = LANE_DETECTION_POSITION;
    char lane_detection_response[] = LANE_DETECTION_RESPONSE;
    char lane_to_recorder[] = "/tmp/lane_to_recorder";
    char lanes_to_pp[] = "/tmp/lanes_to_pp";
    char motor_to_comm[] = MOTOR_TO_COMM;
    char object_to_recorder[] = "/tmp/object_to_recorder";
    char objects_to_pp[] = "/tmp/objects_to_pp";
    char other_freq_to_pid[] = OTHER_FREQ_TO_PID;
    char parser_to_motor[] = PARSER_TO_MOTOR;
    char parser_to_platoon[] = PARSER_TO_PLATOON;
    char platooning_dist_pipe[] = PLATOONING_DIST_PIPE;
    char platooning_pid_to_motor[] = PLATOONING_PID_TO_MOTOR;
    char platooning_state_to_pid[] = PLATOONING_STATE_TO_PID;
    char platooning_to_motor[] = PLATOONING_TO_MOTOR;
    char platooning_to_recorder[] = "/tmp/platooning_to_recorder";
    char platooning_vel_pipe[] = PLATOONING_VEL_PIPE;
    char pp_to_LD_controller[] = "/tmp/pp_to_LD_controller";
    char pp_to_lanes[] = "/tmp/pp_to_lanes";
    char pp_to_motor[] = PP_TO_MOTOR;
    char parser_to_camera[] = "/tmp/parser_to_camera";
    char parser_to_main[] = "/tmp/parser_to_main";

    printStartUpMessages();

    //TODO Delete all pipes at start!
    if(OBJECT_DETECTION) {	
        if (makeFifo(camera_to_LD) == -1) {
            fprintf(stderr, "Failed to make CAMERA_TO_LD!\n");
            exit(-1);
        }
        if (makeFifo(camera_to_OD) == -1) {
            fprintf(stderr, "Failed to make CAMERA_TO_OD!\n");
            exit(-1);
        }
        // The following 3 pipes are needed for platooning
        if (makeFifo(camera_to_Platooning) == -1) {
            fprintf(stderr, "Failed to make CAMERA_TO_PLATOONING!\n");
            exit(-1);
        }
        if (makeFifo(camera_to_recorder) == -1) {
            fprintf(stderr, "Failed to make camera_to_recorder!\n");
            exit(-1);
        }
        if (makeFifo(colePipe) == -1) {
            fprintf(stderr, "Failed to make colePipe!\n");
            exit(-1);
        }
        if (makeFifo(comm_to_lane_change) == -1) {
            fprintf(stderr, "Failed to make comm_to_lane_change!\n");
            exit(-1);
        }
        if (makeFifo(comm_to_platooning_pid) == -1) {
            fprintf(stderr, "Failed to make COMM_TO_PLATOONING_PID!\n");
            exit(-1);
        }
        if (makeFifo(freq_to_controller) == -1) {
            fprintf(stderr, "Failed to make freq_to_controller!\n");
            exit(-1);
        }
        if (makeFifo(freq_to_comm) == -1) {
            fprintf(stderr, "Failed to make freq_to_comm!\n");
            exit(-1);
        }
        if (makeFifo(getting_comm_to_pid) == -1) {
            fprintf(stderr, "Failed to make tmpJacobPipe!\n");
            exit(-1);
        }
        if (makeFifo(lane_change) == -1) {
            fprintf(stderr, "Failed to make lane_change!\n");
            exit(-1);
        }
        if (makeFifo(lane_change_comm) == -1) {
            fprintf(stderr, "Failed to make lane_change_comm!\n");
            exit(-1);
        }
        if (makeFifo(lane_detection_position) == -1) {
            fprintf(stderr, "Failed to make LANE_DETECTION_POSITION!\n");
            exit(-1);
        }
        if (makeFifo(lane_detection_response) == -1) {
            fprintf(stderr, "Failed to make LANE_DETECTION_RESPONSE!\n");
            exit(-1);
        }
        if (makeFifo(lane_to_recorder) == -1) {
            fprintf(stderr, "Failed to make lane_to_recorder!\n");
            exit(-1);
        }
        if (makeFifo(lanes_to_pp) == -1) {
            fprintf(stderr, "Failed to make lanes_to_pp!\n");
            exit(-1);
        }
        if (makeFifo(motor_to_comm) == -1) {
            fprintf(stderr, "Failed to make MOTOR_TO_COMM!\n");
            exit(-1);
        }
        if (makeFifo(object_to_recorder) == -1) {
            fprintf(stderr, "Failed to make object_to_recorder!\n");
            exit(-1);
        }
        if (makeFifo(objects_to_pp) == -1) {
            fprintf(stderr, "Failed to make objects_to_pp!\n");
            exit(-1);
        }
        if (makeFifo(other_freq_to_pid) == -1) {
            fprintf(stderr, "Failed to make other_freq_to_pid!\n");
            exit(-1);
        }
        if (makeFifo(parser_to_camera) == -1) {
            fprintf(stderr, "Failed to make parser_to_camera!\n");
            exit(-1);
        }
        if (makeFifo(parser_to_main) == -1) {
            fprintf(stderr, "Failed to make parser_to_main!\n");
            exit(-1);
        }
        if (makeFifo(parser_to_motor) == -1) {
            fprintf(stderr, "Failed to make parser_to_motor!\n");
            exit(-1);
        }
        if (makeFifo(parser_to_motor) == -1) {
            fprintf(stderr, "Failed to make PARSER_TO_MOTOR!\n");
            exit(-1);
        }
        if (makeFifo(parser_to_platoon) == -1) {
            fprintf(stderr, "Failed to make PARSER_TO_PLATOON!\n");
            exit(-1);
        }
        if (makeFifo(platooning_dist_pipe) == -1) {
            fprintf(stderr, "Failed to make PLATOONING_DIST_PIPE!\n");
            exit(-1);
        }
        if (makeFifo(platooning_pid_to_motor) == -1) {
            fprintf(stderr, "Failed to make PLATOONING_PID_TO_MOTOR!\n");
            exit(-1);
        }
        if (makeFifo(platooning_state_to_pid) == -1) {
            fprintf(stderr, "Failed to make PLATOONING_STATE_TO_PID!\n");
            exit(-1);
        }
        if (makeFifo(platooning_to_motor) == -1) {
            fprintf(stderr, "Failed to make PLATOONING_TO_MOTOR!\n");
            exit(-1);
        }
        if (makeFifo(platooning_to_recorder) == -1) {
            fprintf(stderr, "Failed to make platooning_to_recorder!\n");
            exit(-1);
        }
        if (makeFifo(platooning_vel_pipe) == -1) {
            fprintf(stderr, "Failed to make PLATOONING_VEL_PIPE!\n");
            exit(-1);
        }
        if (makeFifo(pp_to_LD_controller) == -1) {
            fprintf(stderr, "Failed to make pp_to_lanes!\n");
            exit(-1);
        }
        if (makeFifo(pp_to_lanes) == -1) {
            fprintf(stderr, "Failed to make pp_to_lanes!\n");
            exit(-1);
        }
        if (makeFifo(pp_to_motor) == -1) {
            fprintf(stderr, "Failed to make OBJECT_DETECTION_TO_MOTOR!\n");
            exit(-1);
        }
    }
    parser_to_main_fds[0].fd = parser_to_main_fd;
    parser_to_main_fds[0].events = POLLIN;

    startParser(pids, &subProcesses);
    startLaneKeeping(pids, &subProcesses);
    startPlatooning(pids, &subProcesses);
    startMotor(pids, &subProcesses);

    // Opening pipes
    if ((parser_to_main_fd = open(parser_to_main, O_RDONLY)) == -1) { // out resp
        perror("Main: Failed to open parser_to_main pipe");
        exit(-1);
    }

    // Waiting for quit command
    while (1) {
        read(parser_to_main_fd, buf, 10);
	if (buf[0] == 'q' || buf[0] == 'Q') {
	    break;
	}
        memset(buf, 0, 10);
    }
    
    for (int i=0; i<subProcesses; i++) {
	kill(pids[i], SIGKILL);
	printf("SIGKILL: PROGRAM\n");
    }

    printf("Cleanup complete.\n");
    printf("EXITING: main.cpp\n");
    printf("\n");
    printf("\n");
    printf("All programs ended.\n");
    printf("\n");
    return 0;
}

/* FUNCTIONS */
int startParser(pid_t *pids, int *subProcesses) {
    pid_t pid;
    int fd;
    /* Making parser */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
    }
    if (pid == 0) { // making parser
        execl("./io/parser", "./io/parser", (char *) NULL);
        perror("./io/parser");
        fprintf(stderr, "ERR: Parser brainwash failed\n");
    }
    pids[(*subProcesses)++] = pid;
    return 0;
}

int startPlatooning(pid_t *pids, int *subProcesses) {
    pid_t pid;
    int fd;
    /* Making controller */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
    }
    if (pid == 0) { // making platooning controller
        close(0);
        execl("./controllers/platooningController", "./controllers/platooningController", (char *) NULL);
        perror("./controllers/platooningController");
        fprintf(stderr, "ERR: Platooning controller brainwash failed\n");
    }
    pids[(*subProcesses)++] = pid;
    /* Making comm */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
    }
    if (pid == 0) { // start comm task
        close(0);
        execlp("python", "python", "./io/comm.py", (char *) NULL);
        perror("main: Failed to fork ./io/comm.py");
        printf("ERR: Brainwash failed!\n");
    }
    pids[(*subProcesses)++] = pid;
    return 0;
}

int startLaneKeeping(pid_t *pids, int *subProcesses) {
    pid_t pid;
    int fd;

    /* Making path planning */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
        exit(-1);
    }
    if (pid == 0) { // start path planning
        fprintf(stderr, "Time to exec pathPlanning.py!!!!!!!!!!!!!!!!!!!!\n");
        close(0);
        execlp("python3", "python3", "./pathPlanning.py", (char *) NULL);
        perror("main: Failed to exec pathPlanning.py");
        printf("ERR: Brainwash failed!\n");
    }
    pids[(*subProcesses)++] = pid;
    /* Making lane tracking */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
        exit(-1);
    }
    if (pid == 0) { // start vision tasks
        fprintf(stderr, "Time to exec CAMERA.py!!!!!!!!!!!!!!!!!!!!\n");
        close(0);
        execlp("python3", "python3", "./vision/Camera.py", (char *) NULL);
        //execlp("python3", "python3", "pipePython/exec/tmp.py", (char *) NULL);
        perror("main: Failed to exec ./vision/Camera.py");
        printf("ERR: Brainwash failed!\n");
    }
    pids[(*subProcesses)++] = pid;
    /* Making controller */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
    }
    if (pid == 0) { // making lane tracking controller
        // TODO Open named pipe in file instead of here
        // Close stdin after moving the dup2
        if ((fd = open(LANE_DETECTION_POSITION, O_RDONLY)) == -1) { // read pos //
            perror("main: Failed to open LANE_DETECTION_POSITION pipe");
            exit(-1);
        }
        dup2(fd, 0); // dup read onto stdin
        execl("./controllers/laneDetectionController", "./controllers/laneDetectionController", (char *) NULL);
        perror("./controllers/laneDetectionController");
        fprintf(stderr, "ERR: Lane detection controller brainwash failed\n");
    }
    pids[(*subProcesses)++] = pid;
    /* Making i2c */
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
    }
    if (pid == 0) { // making i2c
        close(0);
        execl("./gpio/i2c", "./gpio/i2c", (char *) NULL);
        perror("./gpio/i2c");
        fprintf(stderr, "ERR: GPIO i2c brainwash failed\n");
    }
    pids[(*subProcesses)++] = pid;
    return 0;
}

int makeFifo(char *fifopath) {
    if ((access(fifopath, F_OK) != -1)) { // if fifo exists
        if (remove(fifopath) == -1) { // delete fifo
            perror("makeLaneDetectionFifo: Failed to delete fifo");
            return -1;
        }
    }
    if (mkfifo(fifopath, 0666) == -1) { // makefifo failed
        perror("makeLaneDetectionFifo: Failed to make fifo");
        return -1;
    }
    return 0;
}

int startMotor(pid_t *pids, int *subProcesses) {
    pid_t pid;
    if ((pid = fork()) == -1) { // fork forked up
        printf("ERR: Fork failed\n");
    }
    if (pid == 0) { // making gpio motor
        close(0);
        execl("./gpio/Motor", "./gpio/Motor", (char *) NULL);
        perror("./gpio/Motor");
        fprintf(stderr, "ERR: GPIO Motor brainwash failed\n");
    }
    pids[(*subProcesses)++] = pid;
    return 0;
}

void printStartUpMessages() {
    if (LANE_KEEPING) {
        printf("Lane keeping: ON\n");
    }
    else {
        printf("Lane keeping: OFF\n");
    }
    if (MOTOR) {
        printf("Motor: ON\n");
    }
    else {
        printf("Motor: OFF\n");
    }
}

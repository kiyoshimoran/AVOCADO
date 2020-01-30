#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <iostream>
#include <sys/poll.h>
#include <sys/types.h>
#include "./jetsonGPIO.h"

//#define scale(x) ((x / 2) + 1) * 1000
#define freq 10000

using namespace std;

int main(int argc, char ** argv)
{
    int dir, rev, up_time, down_time, i, ret;
    char c;
    struct pollfd fds;
    fds.fd = 0;
    jetsonTX2GPIONumber steering = gpio388;
    gpioExport(steering);
    gpioSetDirection(steering, outputPin);
    //pid_t pid = fork();
    // char * argv_m[] = {"./motor", NULL};
    //execv("./motor", argv_m);
    char myBuf[10];
    int numBytes = 10;
    dir = 0;
    while(1)
    {
        fds.events = POLLIN;
        ret = poll(&fds, 1, 0);
        if(ret == 1) {
            //cin >> dir;
            read(0, myBuf, numBytes);
            up_time = atoi(myBuf);
            printf("Read a value of %i\n", up_time);
            down_time = freq - up_time;
            usleep(up_time);
            usleep(down_time);
        }
        //read direction
        /*
        if(dir > 20)
        {
//            cout << "left\n" << flush;
            up_time = 1000;//scale(dir);
            down_time = freq - up_time;
//            gpioSetValue(steering, on);
            usleep(up_time);
//            gpioSetValue(steering, off);
            usleep(down_time);
        }
        else if(dir < -20)
        {
//            cout << "right\n" << flush;
            up_time = 1900;
            down_time = freq - up_time;
//            gpioSetValue(steering, on);
            usleep(up_time);
//            gpioSetValue(steering, off);
            usleep(down_time);
        }
        else
        {
//            cout << "straight\n" << flush;
            up_time = 1550;
            down_time = freq - up_time;
//            gpioSetValue(steering, on);
            usleep(up_time);
//            gpioSetValue(steering, off);
            usleep(down_time);
        }
        */
    }
    gpioUnexport(steering);
    return 0;
}

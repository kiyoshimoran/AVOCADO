#include <stdio.h>
#include <unistd.h>
#include <iostream>
#include <sys/poll.h>
#include <sys/types.h>
#include "jetsonGPIO.h"

//#define scale(x) ((x / 2) + 1) * 1000
#define freq 10000
#define magic 125
#define bonus 300

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
    while(1)
    {
        fds.events = POLLIN;
        ret = poll(&fds, 1, 0);
        if(ret == 1)
            cin >> dir;
        //read direction
        if(dir > 1)
        {
            cout << "left\n" << flush;
            up_time = 990 - magic;//scale(dir);
            down_time = freq - up_time - bonus;
            gpioSetValue(steering, on);
            usleep(up_time);
            gpioSetValue(steering, off);
            usleep(down_time);
        }
        else if(dir == 1)
            break;
        else if(dir < 0)
        {
            cout << "right\n" << flush;
            up_time = 1900 - magic;
            down_time = freq - up_time - bonus;
            gpioSetValue(steering, on);
            usleep(up_time);
            gpioSetValue(steering, off);
            usleep(down_time);
        }
        else
        {
            cout << "straight\n" << flush;
            up_time = 1550 - magic;
            down_time = freq - up_time - bonus;
            gpioSetValue(steering, on);
            usleep(up_time);
            gpioSetValue(steering, off);
            usleep(down_time);
        }
    }
    gpioUnexport(steering);
    return 0;
}

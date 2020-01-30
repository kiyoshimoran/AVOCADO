#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <time.h>
#include <iostream>
#include "jetsonGPIO.h"

using namespace std;

int getFD(char *arg);

int main(int argc, char **argv)
{
    jetsonTX2GPIONumber read = gpio298;
    clock_t timer;
    int wfd, rfd, dir, val, pval, time, up, down, freq, duty;
    char count = 0;
    wfd = getFD(argv[1]);
    rfd = getFD(argv[2]);
    gpioExport(read);
    gpioSetDirection(read, inputPin);
    time = clock();
    while(1)
    {
        pval = val;
        val = gpioGetValue(read, val);
        if(pval != val)
        {
            time = time - clock();
            if(val == 1)
                down = time;
            else if(val == 0)
                up = time;
            count++;
            if(count == 2)
            {
                count = 0;
                duty = up / (up + down);
            }
            cout << duty << flush;
        }
    }
    return 0;
}

int getFD(char *arg)
{
    char fd;
    if(sscanf(arg, "%d", &fd) != 1)
    {
        fprintf("bad fd\n");
        exit(EXIT_FAILURE);
    }
    return fd;
}

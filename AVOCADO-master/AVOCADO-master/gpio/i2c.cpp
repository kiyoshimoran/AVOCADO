#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <unistd.h>
//#include "JHLEDBackpack.h"
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "i2c.h"
#include "../include/pipes/lane_detection_response.h"
#include "../include/pipes/communication.h"
#include "../include/pipes/platoon_pipes.h"

int main()
{
    char nameBuf[32];
    uint8_t cmdBuf[3], freq;
    int read_freq;
    int received = 100;
    int ret, errno, i2cFD, address, numBytes, fd, read_return, freqFD, commFreqFD;
    struct pollfd fds;
    short dir = 155;
    numBytes = sizeof (int);
    address = 8;
    sprintf(nameBuf, "/dev/i2c-%d", 1);
    i2cFD = open(nameBuf, O_RDWR);
    if(i2cFD < 0)
        return -1;
    if(errno = ioctl(i2cFD, I2C_SLAVE, address) < 0)
        return errno;
    int timeout = 1000; // number of ms until poll says failed
    
    if ((commFreqFD = open(FREQ_TO_COMM, O_WRONLY)) == -1) {
        perror("i2c: Failed to open FREQ_TO_COMM pipe");
        exit(EXIT_FAILURE);
    }
    if ((freqFD = open(FREQ_TO_CONTROLLER, O_WRONLY)) == -1) {
        perror("i2c: Failed to open FREQ_TO_CONTROLLER pipe");
        exit(EXIT_FAILURE);
    }
    if ((fd = open(LANE_DETECTION_RESPONSE, O_RDONLY)) == -1) {
        perror("i2c: Failed to open LANE_DETECTION_RESPONSE pipe");
        exit(EXIT_FAILURE);
    }
    fds.fd = fd;

    printf("Starting I2C.cpp\n");
    while(1) {
        //TODO add poll for motor pipe; send data if either val changes
        fds.events = POLLIN;
        ret = poll(&fds, 1, timeout);
        if(ret)
        {
            read_return = read(fd, &received, sizeof(int));
            if(received > 80)
                cmdBuf[0] = received;
            else
                cmdBuf[1] = received;
        }            
	i2c_smbus_write_block_data(i2cFD, 0, 2, (uint8_t *)cmdBuf);
        //i2c_smbus_ioctl_data(i2cFD, 0, 2, (uint8_t *)cmdBuf);

	//TODO add pipe to send motor feedback to pid
        //printf("duty cycle = %d\n", cmdBuf[1]);
        //printf("steering = %d\n", cmdBuf[0]);
        read_freq = (int) i2c_smbus_read_byte(i2cFD) * 2;
        if (read_freq >= 0) {
            //printf("read freq = %d\n", read_freq);
            freq = read_freq;
            //printf("About to write: %i\n", read_freq);
            write(freqFD, &read_freq, sizeof (int));
            write(commFreqFD, &read_freq, sizeof (int));
        }
    }

    return 0;
}

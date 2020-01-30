#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/poll.h>
#include <unistd.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <fcntl.h>


int main()
{
    char nameBuf[32], comBuf[2];
    int s_received = 100, m_recieved = 100;
    int ret, errno, i2cFD, address, numBytes;
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
    //combuf[0] = 's';    // steering command first
    //combuf[2] = 'm';    // motor second
    //comBuf[4] = '\0';   
 
    while(1)
    {
        comBuf[0] = 155;    
        combuf[1] = 50;
        12c_smbus_write_block_data(i2cFD, 0x00, 2, (__u8*)comBuf);
    }
    return 0;
}

#include "jetsonGPIO.h"

int main()
{
    gpioExport(388);
    gpioUnexport(388);
    return 0;
}

#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/poll.h>
#include <sys/wait.h>

using namespace std;

int main()
{
    pid_t pid_s, pid_m;
    int fd_s[2], fd_m[2];
    struct pollfd fds;
    fds.fd = 0;
    fds.events = POLLIN;
    int ret = 1;
    int status;
    pid_s = fork();
    if(pid_s == -1)
    {
        printf("cant fork\n");
        exit(EXIT_FAILURE);
    }
    if(pid_s == 0)
    {
        printf("steering processes created\n");
        char * argv_s[] = {"./steering", NULL};
        execv("./steering", argv_s);
        exit(0);
    }
    else
    {
        pid_m = fork();
        if(pid_m == 0)
        {
            printf("motor process created\n");
            char *argv_m[] = {"./motor", NULL};
            execv("./motor", argv_m);
            exit(0);
        }
        else
        {
            while(1)
            {
                printf("parent/read\n");
                ret = poll(&fds, 1, 0);
                if(ret)
                    break;
            }
        }
    }
    /*else
    {
        printf("parent process\n");
        if(waitpid(pid_s, &status, 0) > 0) 
        {
            if(WIFEXITED(status) && !WEXITSTATUS(status))
                printf("steering exited successfully\n");
            else
                printf("you done fucked up\n");
        }
        else if(waitpid(pid_m, &status, 0) > 0)
        {
            if(WIFEXITED(status) && !WEXITSTATUS(status))
                printf("motor exited successfully\n");
            else
                printf("you done fucked up\n");
        }
    }*/
    exit(0);
    return 0;
}


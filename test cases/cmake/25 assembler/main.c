#include <stdint.h>
#include <stdio.h>

int32_t cmTestFunc();

int main(int argc, char* argv[])
{
    if (cmTestFunc() > 4200)
    {
        printf("Test success.\n");
        return 0;
    }
    else
    {
        printf("Test failure.\n");
        return 1;
    }
}

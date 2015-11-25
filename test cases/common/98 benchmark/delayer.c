/* Simple prog that sleeps for a random time. */

#include<stdlib.h>
#if !defined(_MSC_VER)
#include<time.h>
#else
#include<windows.h>
#endif

int main(int argc, char **argv) {
    srand(time(NULL));
#if !defined(_MSC_VER)
    struct timespec t;
    t.tv_sec = 0;
    t.tv_nsec = 199999999.0*rand()/RAND_MAX;
    nanosleep(&t, NULL);
#else
    Sleep(500.0*rand()/RAND_MAX);
#endif
    return 0;
}

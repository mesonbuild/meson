#include <stdio.h>
#include <signal.h>

void usr1_handler(int signum) {
    printf("%d", signum);
}

int main(){
    signal(SIGUSR1, usr1_handler);

    raise(SIGUSR1);
    return 0;
}

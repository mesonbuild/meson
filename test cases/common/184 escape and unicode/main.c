#include <string.h>

const char* does_it_work();

int a_fun();

int main() {
    if(strcmp(does_it_work(), "yes it does") != 0) {
        return -a_fun();
    }
    return 0;
}

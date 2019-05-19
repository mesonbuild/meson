#include"input_src.h"

int main(int argc, char **argv) {
    void *foo = printf;
    if(foo) {
        return 0;
    }
    return 1;
}

#include"input_src.h"

int main() {
    void *foo = printf;
    if(foo) {
        return 0;
    }
    return 1;
}

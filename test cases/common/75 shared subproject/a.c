#include<assert.h>
char func_b();
char func_c();

int main(int argc, char **argv) {
    if(func_b() != 'b') {
        return 1;
    }
    if(func_c() != 'c') {
        return 2;
    }
    return 0;
}

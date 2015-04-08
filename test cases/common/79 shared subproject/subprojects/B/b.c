#include<stdlib.h>
char func_c();

char func_b() {
    if(func_c() != 'c') {
        exit(3);
    }
    return 'b';
}

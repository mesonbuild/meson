#include <stdio.h>

void hello_from_rust(void);

static void hello_from_c(void) {
    printf("Hello from C!\n");
}

void hello_from_both(void) {
    hello_from_c();
    hello_from_rust();
}

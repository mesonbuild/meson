#include<adder.h>
#include<stdlib.h>

struct _Adder {
    int number;
};

adder* adder_create(int number) {
    adder *a = malloc(sizeof(struct _Adder));
    a->number = number;
    return a;
}

// adder_add is implemented in the Rust file.

void adder_destroy(adder *a) {
    free(a);
}

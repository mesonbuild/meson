#include <stdio.h>

#include <libb.h>

int main() {
    int result = libA_func(1) + libB_func(3);
    printf("The answer is: %d\n", result);
    return result;
}

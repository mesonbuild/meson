#include "library.h"


int main(void)
{
    int sum = library_function();
    return sum == EXPECTED ? 0 : 1;
}

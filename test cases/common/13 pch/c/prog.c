// No includes for the main program, they need to come from the PCH

#include "shared.h"
#include "static.h"

void func(void) {
    fprintf(stdout, "This is a function that fails if stdio is not #included.\n");
}

int main(void) {
    return shared_lrint(0) + static_lrint(neg(0));
}

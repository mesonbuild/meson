#if defined(_MSC_VER)
#include"prog.pch"
#endif

void func() {
    fprintf(stdout, "This is a function that fails if stdio is not #included.\n");
}

int main(int argc, char **argv) {
    return 0;
}

#include "subprojheader.h"
#include "subprojheader-copy.h"

int main(int argc, char **argv) {
    return 3*0xdecaf - subprojfunc() - subprojfunccopy();
}

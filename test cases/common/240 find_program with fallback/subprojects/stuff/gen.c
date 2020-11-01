#include <assert.h>
#include <stdio.h>

int main(int argc, char **argv) {
    assert(argc == 3);
    FILE *fp = fopen(argv[2], "wb");
    fprintf(fp, "#include <stdio.h>\n");
    fprintf(fp,
    "int main(void)\n"
    "{\n"
    "    puts(\"hello, %s!\");\n"
    "}\n", argv[1]
    );
}


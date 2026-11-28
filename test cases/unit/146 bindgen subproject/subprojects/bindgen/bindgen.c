#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    for (int i = 1; i + 1 < argc; ++i) {
        if (strcmp(argv[i], "--output") == 0) {
            FILE *out = fopen(argv[i + 1], "w");
            if (!out)
                return 1;
            fputs("pub const VALUE: u32 = 42;\n", out);
            return fclose(out) != 0;
        }
    }
    /* No configure-time version or target probes are supported. */
    return 1;
}

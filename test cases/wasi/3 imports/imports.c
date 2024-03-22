#include <stdio.h>
#include <stdlib.h>

extern int console_log(char const *const message);

int main(int argc, char **argv) {
  size_t buffer_len = 256;
  char *buffer = malloc(sizeof(*buffer) * buffer_len);
  if (!buffer) {
    console_log("Not enough memory!");
    return -1;
  }
  snprintf(buffer, buffer_len,
           "See how I customize this %zu-character message!", buffer_len);
  console_log(buffer);
  free(buffer);
  return 0;
}

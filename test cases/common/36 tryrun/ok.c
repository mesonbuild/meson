#include<stdio.h>
int main(int argc, char **argv) {
  printf("%s\n", "stdout");
  fprintf(stderr, "%s\n", "stderr");
  return 0;
}

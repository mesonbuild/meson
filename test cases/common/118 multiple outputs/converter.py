#!/usr/bin/env python3

import sys

basename = sys.argv[1]
open("{}.cpp".format(basename)).write("""
#include<stdio.h>

int main(int argc, char **argv) {
  printf("I was made from {0}.\n");
  return 0;
}
""".format(basename))

open("{}.h".format(basename)).write("""
int main(int argc, char **argv);
""")

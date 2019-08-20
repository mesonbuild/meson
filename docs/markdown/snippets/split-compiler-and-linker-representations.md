## Compiler and dynamic linker representation split

0.52.0 inclues a massive refactor of the representaitons of compilers to
tease apart the representations of compilers and dynamic linkers (ld). This
fixes a number of compiler/linker combinations. In particular this fixes
use GCC and vanilla clang on macOS.
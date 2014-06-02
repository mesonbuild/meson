This test checks that a pre-existing object file can be used in projects.
In order to do this, we need prebuilt objects in the source dir. To enable
a new platform, the source file source.c needs to be compiled and then
the Meson file updated to use it.

The object needs to be built with no optimization and debug symbols enabled.
As an example, this is what a compile command with Gcc on x86 Linux would
look like:

gcc -c -g -o linux-i386.o source.c

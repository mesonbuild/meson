## Add support for prelinked static libraries

The static library gains a new `prelink` keyword argument that can be
used to prelink object files in that target. This is currently only
supported for the GNU toolchain, patches to add it to other compilers
are most welcome.

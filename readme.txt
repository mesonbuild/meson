This is an experiment to examine what would be
the optimal syntax for a cross-platform build
system.

Dependencies: Python3 and Python-Ply

Running:

Builder requires that you have a source directory and a build directory
and that these two are different. In your source root must exist a file
called 'builder.txt'. To generate the build system run this command:

builder.py <source directory> <build directory>

You can omit either of the two directories, and Builder will subsitute
the current directory and autodetect what you mean. This mean that you
can do things like this:

cd source_root; mkdir build; cd build; builder ..
cd source_root; mkdir build; builder build

For questions contact jpakkane@gmail.com.

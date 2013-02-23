This is an experiment to examine what would be
the optimal syntax for a cross-platform build
system.

Dependencies: Python3 and Python-Ply

Running:

Meson requires that you have a source directory and a build directory
and that these two are different. In your source root must exist a file
called 'meson.build'. To generate the build system run this command:

meson.py <source directory> <build directory>

You can omit either of the two directories, and Meson will substitute
the current directory and autodetect what you mean. This mean that you
can do things like this:

cd source_root; mkdir build; cd build; meson.py ..
cd source_root; mkdir build; meson.py build

For questions contact the mailing list at
https://lists.sourceforge.net/lists/listinfo/meson-devel

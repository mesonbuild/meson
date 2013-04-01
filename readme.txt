This is an experiment to examine what would be
the optimal syntax for a cross-platform build
system.

Dependencies

Python 3.3: http://python.org
Python-Ply: http://www.dabeaz.com/ply/ply.html
Ninja:      http://martine.github.com/ninja/

Installing from source

You can run Meson directly from a revision control checkout.
Installing it system-wide is simple.

Configure step: None
Compile step:   ./compile_meson.py
Unit test step: ./run_tests.py
Install step:   [sudo] ./install_meson.py --prefix /your/prefix --destdir /destdir/path

The default value of prefix is /usr/local. The default value of destdir
is empty. 

Running:

Meson requires that you have a source directory and a build directory
and that these two are different. In your source root must exist a file
called 'meson.build'. To generate the build system run this command:

meson <source directory> <build directory>

You can omit either of the two directories, and Meson will substitute
the current directory and autodetect what you mean. This mean that you
can do things like this:

cd source_root; mkdir build; cd build; meson.py ..
cd source_root; mkdir build; meson.py build

To compile, cd into your build directory and type 'ninja'. To run unit
tests, type 'ninja test'.

Install is the same but it can take an extra argument:

DESTDIR=/destdir/path ninja install

DESTDIR can be omitted. If you are installing to system directories,
you may need to run this command with sudo.


Contact info

All questions should be sent to the mailing list:
https://lists.sourceforge.net/lists/listinfo/meson-devel

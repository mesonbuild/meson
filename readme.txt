Meson® is project to create the best possible next-generation
build system.


Dependencies

Python   http://python.org (version 3.3 or newer)
Ninja    http://martine.github.com/ninja/


Installing from source

You can run Meson directly from a revision control checkout or an
extracted tarball.  Installing it system-wide is simple.

Configure step: None
Compile step:   None
Unit test step: nosetests-3.4 -v .
Install step:   [sudo] ./install_meson.py --prefix /your/prefix --destdir /destdir/path

The default value of prefix is /usr/local. The default value of destdir
is empty. 


Running

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


Contributing

We love code contributions. See the contributing.txt file for
details.


Further info

The home page of Meson can be found here:

https://jpakkane.github.io/meson/

Meson is a registered trademark of Jussi Pakkanen

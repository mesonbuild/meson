<p align="center">
<img src="http://mesonbuild.com/meson_logo.png">
</p>
Meson® is a project to create the best possible next-generation
build system.

####Dependencies

 - [Python](http://python.org) (version 3.4 or newer)
 - [Ninja](http://martine.github.com/ninja/)

####Installing from source

You can run Meson directly from a revision control checkout or an
extracted tarball. If you wish you can install it locally with the
standard Python distutils command `python3 setup.py install <your
options here>`.

Meson is also available from
[PyPi](https://pypi.python.org/pypi/meson), so it can be installed
with `pip3 install meson` (this does not require a source checkout,
pip will download the package automatically). The exact command to
type to install with pip can very between systems, be sure to use the
Python 3 version of pip.

####Running

Meson requires that you have a source directory and a build directory
and that these two are different. In your source root must exist a file
called 'meson.build'. To generate the build system run this command:

`meson <source directory> <build directory>`

You can omit either of the two directories, and Meson will substitute
the current directory and autodetect what you mean. This allows you to
do things like this:

`cd source_root; mkdir build; cd build; meson ..`

or

`cd source_root; mkdir build; meson build`

To compile, cd into your build directory and type `ninja`. To run unit
tests, type `ninja test`.

Install is the same but it can take an extra argument:

`DESTDIR=/destdir/path ninja install`

`DESTDIR` can be omitted. If you are installing to system directories,
you may need to run this command with sudo.


####Contributing

We love code contributions. See the contributing.txt file for
details.


####IRC

The irc channel for Meson is `#mesonbuild` over at Freenode.


####Further info

More information about the Meson build system can be found at the
[project's home page](http://mesonbuild.com).

Meson is a registered trademark of Jussi Pakkanen

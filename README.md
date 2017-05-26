<p align="center">
<img src="http://mesonbuild.com/assets/images/meson_logo.png">
</p>
Meson® is a project to create the best possible next-generation
build system.

#### Status

[![PyPI](https://img.shields.io/pypi/v/meson.svg)](https://pypi.python.org/pypi/meson)
[![Travis](https://travis-ci.org/mesonbuild/meson.svg?branch=master)](https://travis-ci.org/mesonbuild/meson)
[![Appveyor](https://ci.appveyor.com/api/projects/status/l5c8v71ninew2i3p?svg=true)](https://ci.appveyor.com/project/jpakkane/meson)
[![Codecov](https://codecov.io/gh/mesonbuild/meson/coverage.svg?branch=master)](https://codecov.io/gh/mesonbuild/meson/branch/master)

#### Dependencies

 - [Python](http://python.org) (version 3.4 or newer)
 - [Ninja](https://ninja-build.org) (version 1.5 or newer)

#### Installing from source

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

#### Running

Meson requires that you have a source directory and a build directory
and that these two are different. In your source root must exist a file
called 'meson.build'. To generate the build system run this command:

`meson <source directory> <build directory>`

Depending on how you obtained Meson the command might also be called
`meson.py` instead of plain `meson`. In the rest of this document we
are going to use the latter form.

You can omit either of the two directories, and Meson will substitute
the current directory and autodetect what you mean. This allows you to
do things like this:

`cd source_root; mkdir builddir; cd builddir; meson ..`

or

`cd source_root; mkdir builddir; meson builddir`

To compile, cd into your build directory and type `ninja`. To run unit
tests, type `ninja test`.

Install is the same but it can take an extra argument:

`DESTDIR=/destdir/path ninja install`

`DESTDIR` can be omitted. If you are installing to system directories,
you may need to run this command with sudo.


#### Contributing

We love code contributions. See the contributing.txt file for
details.


#### IRC

The irc channel for Meson is `#mesonbuild` over at Freenode.


#### Further info

More information about the Meson build system can be found at the
[project's home page](http://mesonbuild.com).

Meson is a registered trademark of Jussi Pakkanen

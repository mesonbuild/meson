---
title: Quick guide
short-description: Guide to get started using meson
...

# Using Meson

Meson has been designed to be as easy to use as possible. This page
outlines the basic use cases. For more advanced cases refer to Meson's
command line help which is accessible with the command `meson --help`.

Requirements
--

Meson has two main dependencies.

* [Python 3](https://python.org)
* [Ninja](https://github.com/ninja-build/ninja/)

Ninja is only needed if you use the Ninja backend. Meson can also
generate native VS and XCode project files.

On Ubuntu these can be easily installed with the following command:

```console
$ sudo apt-get install python3 ninja-build
```

The best way to get Meson is to `pip install` it for your user

```console
$ pip3 install --user meson
```

You can also use Meson as packaged by your distro, but beware that due
to our frequent release cycle and development speed this version might
be out of date.

Another option is to clone the git repository and run it directly from
there.

Compiling a Meson project
--

The most common use case of Meson is compiling code on a code base you
are working on. The steps to take are very simple.

```console
$ cd /path/to/source/root
$ meson builddir && cd builddir
$ ninja
$ ninja test
```

The only thing to note is that you need to create a separate build
directory. Meson will not allow you to build source code inside your
source tree. All build artifacts are stored in the build
directory. This allows you to have multiple build trees with different
configurations at the same time. This way generated files are not
added into revision control by accident.

To recompile after code changes, just type `ninja`. The build command
is always the same. You can do arbitrary changes to source code and
build system files and Meson will detect those and will do the right
thing. If you want to build optimized binaries, just use the argument
`--buildtype=debugoptimized` when running Meson. It is recommended
that you keep one build directory for unoptimized builds and one for
optimized ones. To compile any given configuration, just go into the
corresponding build directory and run `ninja`.

Meson will automatically add compiler flags to enable debug
information and compiler warnings (i.e. `-g` and `-Wall`). This means
the user does not have to deal with them and can instead focus on
coding.

Using Meson as a distro packager
--

See [the distributors page](Distributors.md) for more information.

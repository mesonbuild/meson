---
short-description: Installing targets
...

# Installing

Invoked via the [following command](Commands.md#install) *(available
since 0.47.0)*:

```sh
meson install
```

or alternatively (on older Meson versions with `ninja` backend):

```sh
ninja install
```

By default Meson will not install anything. Build targets can be
installed by tagging them as installable in the definition.

```meson
project('install', 'c')
shared_library('mylib', 'libfile.c', install : true)
```

There is usually no need to specify install paths or the like. Meson
will automatically install it to the standards-conforming location. In
this particular case the executable is installed to the `bin`
subdirectory of the install prefix. However if you wish to override
the install dir, you can do that with the `install_dir` argument.

```meson
executable('prog', 'prog.c', install : true, install_dir : 'my/special/dir')
```

Other install commands are the following.

```meson
install_headers('header.h', subdir : 'projname') # -> include/projname/header.h
install_man('foo.1') # -> share/man/man1/foo.1
install_data('datafile.dat', install_dir : get_option('datadir') / 'progname')
# -> share/progname/datafile.dat
```

`install_data()` supports rename of the file *since 0.46.0*.

```meson
# file.txt -> {datadir}/{projectname}/new-name.txt
install_data('file.txt', rename : 'new-name.txt')

# file1.txt -> share/myapp/dir1/data.txt
# file2.txt -> share/myapp/dir2/data.txt
install_data(['file1.txt', 'file2.txt'],
             rename : ['dir1/data.txt', 'dir2/data.txt'],
             install_dir : 'share/myapp')
```

Sometimes you want to copy an entire subtree directly. For this use
case there is the `install_subdir` command, which can be used like
this.

```meson
install_subdir('mydir', install_dir : 'include') # mydir subtree -> include/mydir
```

Most of the time you want to install files relative to the install
prefix. Sometimes you need to go outside of the prefix (such as writing
files to `/etc` instead of `/usr/etc`. This can be accomplished by
giving an absolute install path.

```meson
install_data(sources : 'foo.dat', install_dir : '/etc') # -> /etc/foo.dat
```

## Custom install script

Sometimes you need to do more than just install basic targets. Meson
makes this easy by allowing you to specify a custom script to execute
at install time. As an example, here is a script that generates an
empty file in a custom directory.

```bash
#!/bin/sh

mkdir "${DESTDIR}/${MESON_INSTALL_PREFIX}/mydir"
touch "${DESTDIR}/${MESON_INSTALL_PREFIX}/mydir/file.dat"
```

As you can see, Meson sets up some environment variables to help you
write your script (`DESTDIR` is not set by Meson, it is inherited from
the outside environment). In addition to the install prefix, Meson
also sets the variables `MESON_SOURCE_ROOT` and `MESON_BUILD_ROOT`.

Telling Meson to run this script at install time is a one-liner.

```meson
meson.add_install_script('myscript.sh')
```

The argument is the name of the script file relative to the current
subdirectory.

## DESTDIR support

Sometimes you need to install to a different directory than the
install prefix. This is most common when building rpm or deb
packages. This is done with the `DESTDIR` environment variable and it
is used just like with other build systems:

```console
$ DESTDIR=/path/to/staging/area meson install
```

Since *0.57.0* `--destdir` argument can be used instead of environment. In that
case Meson will set `DESTDIR` into environment when running install scripts.

Since *0.60.0* `DESTDIR` and `--destdir` can be a path relative to build
directory. An absolute path will be set into environment when executing scripts.

## Custom install behaviour

Installation behaviour can be further customized using additional
arguments.

For example, if you wish to install the current setup without
rebuilding the code (which the default install target always does) and
only installing those files that have changed, you would run this
command in the build tree:

```console
$ meson install --no-rebuild --only-changed
```

## Installation tags

*Since 0.60.0*

It is possible to install only a subset of the installable files using
`meson install --tags tag1,tag2` command line. When `--tags` is specified, only
files that have been tagged with one of the tags are going to be installed.

This is intended to be used by packagers (e.g. distributions) who typically
want to split `libfoo`, `libfoo-dev` and `libfoo-doc` packages. Instead of
duplicating the list of installed files per category in each packaging system,
it can be maintained in a single place, directly in upstream `meson.build` files.

Meson sets predefined tags on some files. More tags are likely to be added over
time, please help extending the list of well known categories.
- `devel`:
  * `static_library()`,
  * `install_headers()`,
  * `pkgconfig.generate()`,
  * `gnome.generate_gir()` - `.gir` file,
  * Files installed into `libdir` and with `.a` or `.pc` extension,
  * File installed into `includedir`.
- `runtime`:
  * `executable()`,
  * `shared_library()`,
  * `shared_module()`,
  * `jar()`,
  * Files installed into `bindir`.
  * Files installed into `libdir` and with `.so` or `.dll` extension.
- `python-runtime`:
  * `python.install_sources()`.
- `man`:
  * `install_man()`.
- `doc`:
  * `gnome.gtkdoc()`,
  * `hotdoc.generate_doc()`.
- `i18n`:
  * `i18n.gettext()`,
  * `qt.compile_translations()`,
  * Files installed into `localedir`.
- `typelib`:
  * `gnome.generate_gir()` - `.typelib` file.

Custom installation tag can be set using the `install_tag` keyword argument
on various functions such as `custom_target()`, `configure_file()`,
`install_subdir()` and `install_data()`. See their respective documentation
in the reference manual for details. It is recommended to use one of the
predefined tags above when possible.

Installable files that have not been tagged either automatically by Meson, or
manually using `install_tag` keyword argument won't be installed when `--tags`
is used. They are reported at the end of `<builddir>/meson-logs/meson-log.txt`,
it is recommended to add missing `install_tag` to have a tag on each installable
files.

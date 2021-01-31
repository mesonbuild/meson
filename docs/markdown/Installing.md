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

## Custom install behavior

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

## Finer control over install locations

Sometimes it is necessary to only install a subsection of output files
or install them in different directories. This can be done by
specifying `install_dir` as an array rather than a single string. The
array must have as many items as there are outputs and each entry
specifies how the corresponding output file should be installed. For
example:

```meson
custom_target(...
    output: ['file1', 'file2', 'file3'],
    install_dir: ['path1', false, 'path3'],
    ...
)
```

In this case `file1` would be installed to `/prefix/path1/file1`,
`file2` would not be installed at all and `file3` would be installed
to `/prefix/path3/file3'.

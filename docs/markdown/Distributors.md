---
title: Distributors
short-description: Guide for distributors using meson
...

# Using Meson

Distro packagers usually want total control on the build flags
used. Meson supports this use case natively. The commands needed to
build and install Meson projects are the following.

```console
$ cd /path/to/source/root
$ CFLAGS=... CXXFLAGS=... LDFLAGS=.. meson --prefix /usr --buildtype=plain builddir
$ ninja -v -C builddir
$ ninja -C builddir test
$ DESTDIR=/path/to/staging/root ninja -C builddir install
```

The command line switch `--buildtype=plain` tells Meson not to add its
own flags to the command line. This gives the packager total control
on used flags.

This is very similar to other build systems. The only difference is
that the `DESTDIR` variable is passed as an environment variable
rather than as an argument to `ninja install`.

As distro builds happen always from scratch, we recommend you to
enable [unity builds](Unity-builds.md) whenever possible on your
packages because they are faster and produce better code.

## Overriding Default Directories

Many distributions differ in their directory layout so as of Meson 0.45.0 we expose
an easy method of overriding the default behavior. The reason you would want to
override these is *not* for packages it is for users building software on the distro
as they expect `meson` without any specified arguments to go into the right location.
In build scripts for packages it should explicitly set any directories especially `prefix`.

Inside the `mesonbuild` python module you can create a `distro_directories.py` file
and `meson` will import the `default_directories` dictionary from that and
override the internal defaults. As such it can do any arbitrary task such as
checking the architecture at runtime.

The list of these directories as well as their descriptions and defaults can be found
in `meson --help` or alternatively in `default_directories` in `mesonlib.py`.

Some simple examples:

```python
default_directories = {
  'libdir': 'lib',  # Avoid the lib64 heuristics in meson
  'libexecdir': 'lib',  # Some distros don't have a dedicated libexec
}
```

```python
import platform

if platform.machine() in ('x86_64', 'aarch64'):
    libdir = 'lib64'
else:
    libdir = 'lib'


default_directories = {
  'libdir': libdir,
}
```

```python
import subprocess

pc = subprocess.Popen(['dpkg-architecture', '-qDEB_HOST_MULTIARCH'],
                      stdout=subprocess.PIPE,
                      stderr=subprocess.DEVNULL)
(stdo, _) = pc.communicate()
assert pc.returncode == 0
archpath = stdo.decode().strip()
libdir = 'lib/' + archpath

default_directories = {
  'libdir': libdir,
}
```
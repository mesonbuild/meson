## Autogeneration of simple meson.build files

A feature to generate a meson.build file compiling given C/C++ source
files into a single executable has been added to "meson init". By
default, it will take all recognizable source files in the current
directory.  You can also specify a list of dependencies with the -d
flag and automatically invoke a build with the -b flag to check if the
code builds with those dependencies. 

For example,

```meson
meson init -fbd sdl2,gl
```

will look for C or C++ files in the current directory, generate a
meson.build for them with the dependencies of sdl2 and gl and
immediately try to build it, overwriting any previous meson.build and
build directory.

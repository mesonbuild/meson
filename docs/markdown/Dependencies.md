---
short-description: Dependencies for external libraries and frameworks
...

# Dependencies

Very few applications are fully self-contained, but rather they use
external libraries and frameworks to do their work. Meson makes it
very easy to find and use external dependencies. Here is how one would
use the zlib compression library.

```meson
zdep = dependency('zlib', version : '>=1.2.8')
exe = executable('zlibprog', 'prog.c', dependencies : zdep)
```

First Meson is told to find the external library `zlib` and error out
if it is not found. The `version` keyword is optional and specifies a
version requirement for the dependency. Then an executable is built
using the specified dependency. Note how the user does not need to
manually handle compiler or linker flags or deal with any other
minutiae.

If you have multiple dependencies, pass them as an array:

```meson
executable('manydeps', 'file.c', dependencies : [dep1, dep2, dep3, dep4])
```

If the dependency is optional, you can tell Meson not to error out if
the dependency is not found and then do further configuration.

```meson
opt_dep = dependency('somedep', required : false)
if opt_dep.found()
  # Do something.
else
  # Do something else.
endif
```

You can pass the `opt_dep` variable to target construction functions
whether the actual dependency was found or not. Meson will ignore
non-found dependencies.

Meson also allows to get variables that are defined in the
`pkg-config` file. This can be done by using the
`get_pkgconfig_variable` function.

```meson
zdep_prefix = zdep.get_pkgconfig_variable('prefix')
```

These variables can also be redefined by passing the `define_variable`
parameter, which might be useful in certain situations:

```meson
zdep_prefix = zdep.get_pkgconfig_variable('libdir', define_variable: ['prefix', '/tmp'])
```

The dependency detector works with all libraries that provide a
`pkg-config` file. Unfortunately several packages don't provide
pkg-config files. Meson has autodetection support for some of these,
and they are described later on this page.

# Declaring your own

You can declare your own dependency objects that can be used
interchangeably with dependency objects obtained from the system. The
syntax is straightforward:

```meson
my_inc = include_directories(...)
my_lib = static_library(...)
my_dep = declare_dependency(link_with : my_lib,
  include_directories : my_inc)
```

This declares a dependency that adds the given include directories and
static library to any target you use it in.

# Building dependencies as subprojects

Many platforms do not provide a system package manager. On these
systems dependencies must be compiled from source. Meson's subprojects
make it simple to use system dependencies when they are available and
to build dependencies manually when they are not.

To make this work, the dependency must have Meson build definitions
and it must declare its own dependency like this:

    foo_dep = declare_dependency(...)

Then any project that wants to use it can write out the following
declaration in their main `meson.build` file.

    foo_dep = dependency('foo', fallback : ['foo', 'foo_dep'])

What this declaration means is that first Meson tries to look up the
dependency from the system (such as by using pkg-config). If it is not
available, then it builds subproject named `foo` and from that
extracts a variable `foo_dep`. That means that the return value of
this function is either an external or an internal dependency
object. Since they can be used interchangeably, the rest of the build
definitions do not need to care which one it is. Meson will take care
of all the work behind the scenes to make this work.

# Dependencies with custom lookup functionality

## Boost

Boost is not a single dependency but rather a group of different
libraries. To use Boost headers-only libraries, simply add Boost as a
dependency.

```meson
boost_dep = dependency('boost')
exe = executable('myprog', 'file.cc', dependencies : boost_dep)
```

To link against boost with Meson, simply list which libraries you would like to
use.

```meson
boost_dep = dependency('boost', modules : ['thread', 'utility'])
exe = executable('myprog', 'file.cc', dependencies : boost_dep)
```

You can call `dependency` multiple times with different modules and
use those to link against your targets.

If your boost headers or libraries are in non-standard locations you
can set the BOOST_ROOT, BOOST_INCLUDEDIR, and/or BOOST_LIBRARYDIR
environment variables.

You can set the argument `threading` to `single` to use boost libraries that
has been compiled for single-threaded use instead.

## GTest and GMock

GTest and GMock come as sources that must be compiled as part of your
project. With Meson you don't have to care about the details, just
pass `gtest` or `gmock` to `dependency` and it will do everything for
you. If you want to use GMock, it is recommended to use GTest as well,
as getting it to work standalone is tricky.

You can set the `main` keyword argument to `true` to use the `main()`
function provided by GTest:
```
gtest_dep = dependency('gtest', main : true, required : false)
e = executable('testprog', 'test.cc', dependencies : gtest_dep)
test('gtest test', e)
```
## MPI

MPI is supported for C, C++ and Fortran. Because dependencies are
language-specific, you must specify the requested language using the
`language` keyword argument, i.e.,
 * `dependency('mpi', language='c')` for the C MPI headers and libraries
 * `dependency('mpi', language='cpp')` for the C++ MPI headers and libraries
 * `dependency('mpi', language='fortran')` for the Fortran MPI headers and libraries

Meson prefers pkg-config for MPI, but if your MPI implementation does
not provide them, it will search for the standard wrapper executables,
`mpic`, `mpicxx`, `mpic++`, `mpifort`, `mpif90`, `mpif77`. If these
are not in your path, they can be specified by setting the standard
environment variables `MPICC`, `MPICXX`, `MPIFC`, `MPIF90`, or
`MPIF77`, during configuration.

## Qt5

Meson has native Qt5 support. Its usage is best demonstrated with an
example.

```meson
qt5_mod = import('qt5')
qt5widgets = dependency('qt5', modules : 'Widgets')

processed = qt5_mod.preprocess(
  moc_headers : 'mainWindow.h',   # Only headers that need moc should be put here
  moc_sources : 'helperFile.cpp', # must have #include"moc_helperFile.cpp"
  ui_files    : 'mainWindow.ui',
  qresources  : 'resources.qrc',
)

q5exe = executable('qt5test',
  sources     : ['main.cpp',
                 'mainWindow.cpp',
                 processed],
  dependencies: qt5widgets)
```

Here we have an UI file created with Qt Designer and one source and
header file each that require preprocessing with the `moc` tool. We
also define a resource file to be compiled with `rcc`. We just have to
tell Meson which files are which and it will take care of invoking all
the necessary tools in the correct order, which is done with the
`preprocess` method of the `qt5` module. Its output is simply put in
the list of sources for the target. The `modules` keyword of
`dependency` works just like it does with Boost. It tells which
subparts of Qt the program uses.

## Dependencies using config tools

CUPS, LLVM, PCAP, WxWidgets, libwmf, and GnuStep either do not provide
pkg-config modules or additionally can be detected via a config tool
(cups-config, llvm-config, etc). Meson has native support for these tools, and
then can be found like other dependencies:

```meson
pcap_dep = dependency('pcap', version : '>=1.0')
cups_dep = dependency('cups', version : '>=1.4')
llvm_dep = dependency('llvm', version : '>=4.0')
```

Some of these tools (like wmf and cups) provide both pkg-config and config
tools support. You can force one or another via the method keyword:

```meson
wmf_dep = dependency('wmf', method : 'config-tool')
```

## LLVM

Meson has native support for LLVM going back to version LLVM version 3.5. 
It supports a few additional features compared to other config-tool based
dependencies.

As of 0.44.0 Meson supports the `static` keyword argument for LLVM. Before this
LLVM >= 3.9 would always dynamically link, while older versions would
statically link, due to a quirk in `llvm-config`.

### Modules, a.k.a. Components

Meson wraps LLVM's concept of components in it's own modules concept.
When you need specific components you add them as modules as meson will do the
right thing:

```meson
llvm_dep = dependency('llvm', version : '>= 4.0', modules : ['amdgpu'])
```

As of 0.44.0 it can also take optional modules (these will affect the arguments
generated for a static link):

```meson
llvm_dep = dependency(
  'llvm', version : '>= 4.0', modules : ['amdgpu'], optional_modules : ['inteljitevents'],
)
```

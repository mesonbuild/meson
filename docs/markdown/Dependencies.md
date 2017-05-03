---
short-description: Dependencies for external libraries and frameworks
...

# Dependencies

Very few applications are fully self-contained, but rather they use external libraries and frameworks to do their work. Meson makes it very easy to find and use external dependencies. Here is how one would use the zlib compression library.

```meson
zdep = dependency('zlib', version : '>=1.2.8')
exe = executable('zlibprog', 'prog.c', dependencies : zdep)
```

First Meson is told to find the external library `zlib` and error out if it is not found. The `version` keyword is optional and specifies a version requirement for the dependency. Then an executable is built using the specified dependency. Note how the user does not need to manually handle compiler or linker flags or deal with any other minutiae.

If you have multiple dependencies, pass them as an array:

```meson
executable('manydeps', 'file.c', dependencies : [dep1, dep2, dep3, dep4])
```

If the dependency is optional, you can tell Meson not to error out if the dependency is not found and then do further configuration.

```meson
opt_dep = dependency('somedep', required : false)
if opt_dep.found()
  # Do something.
else
  # Do something else.
endif
```

You can pass the `opt_dep` variable to target construction functions whether the actual dependency was found or not. Meson will ignore non-found dependencies.

The dependency detector works with all libraries that provide a `pkg-config` file. Unfortunately several packages don't provide pkg-config files. Meson has autodetection support for some of these.

## Boost ##

Boost is not a single dependency but rather a group of different libraries. To use Boost with Meson, simply list which Boost modules you would like to use.

```meson
boost_dep = dependency('boost', modules : ['thread', 'utility'])
exe = executable('myprog', 'file.cc', dependencies : boost_dep)
```

You can call `dependency` multiple times with different modules and use those to link against your targets.

If your boost headers or libraries are in non-standard locations you can set the BOOST_ROOT, BOOST_INCLUDEDIR, and/or BOOST_LIBRARYDIR environment variables.

## GTest and GMock ##

GTest and GMock come as sources that must be compiled as part of your project. With Meson you don't have to care about the details, just pass `gtest` or `gmock` to `dependency` and it will do everything for you. If you want to use GMock, it is recommended to use GTest as well, as getting it to work standalone is tricky.

## Qt5 ##

Meson has native Qt5 support. Its usage is best demonstrated with an example.

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

Here we have an UI file created with Qt Designer and one source and header file each that require preprocessing with the `moc` tool. We also define a resource file to be compiled with `rcc`. We just have to tell Meson which files are which and it will take care of invoking all the necessary tools in the correct order, which is done with the `preprocess` method of the `qt5` module. Its output is simply put in the list of sources for the target. The `modules` keyword of `dependency` works just like it does with Boost. It tells which subparts of Qt the program uses.

## Declaring your own

You can declare your own dependency objects that can be used interchangeably with dependency objects obtained from the system. The syntax is straightforward:

```meson
my_inc = include_directories(...)
my_lib = static_library(...)
my_dep = declare_dependency(link_with : my_lib,
  include_directories : my_inc)
```

This declares a dependency that adds the given include directories and static library to any target you use it in.

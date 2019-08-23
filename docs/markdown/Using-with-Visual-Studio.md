---
short-description: How to use meson in Visual Studio
...

# Using with Visual Studio

In order to generate Visual Studio projects, Meson needs to know the settings
of your installed version of Visual Studio. The only way to get this
information is to run Meson under the Visual Studio Command Prompt. The steps
to set it up are as follows:

1. Click on start menu and select "Visual Studio 2015 Command Prompt"
1. cd into your source directory
1. mkdir builddir
1. py -3 path/to/meson.py builddir --backend vs2015

If you wish to use the Ninja backend instead of vs2015, pass `--backend
ninja`. At the time of writing the Ninja backend is more mature than the VS
backend so you might want to use it for serious work.

This assumes the py launcher is in your `PATH`, which is highly recommended.

# Using Clang-CL with Visual Studio

*(new in 0.52.0)*

You will first need to get a copy of llvm+clang for Windows, such versions
are available from a number of sources, including the llvm website. Then you
will need the [llvm toolset extension for visual
studio](https://marketplace.visualstudio.com/items?itemName=LLVMExtensions.llvm-toolchain).
You then need to either use a [native file](Native-environments.md#binaries)
or `set CC=clang-cl`, and `set CXX=clang-cl` to use those compilers, meson
will do the rest.

This only works with visual studio 2017 and 2019.

There is currently no support in meson for clang/c2.

# Using Intel-CL (ICL) with Visual Studio

*(new in 0.52.0)*

To use ICL you need only have ICL installed and launch an ICL development
shell like you would for the ninja backend and meson will take care of it.

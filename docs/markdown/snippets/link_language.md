## `link_language` target options
There may be situations for which the user wishes to manually specify the linking language.
For example, a C++ target may link C, Fortran, etc. and perhaps the automatic detection in Meson does not pick the desired compiler.
The user can manually choose the linker by language per-target like this example of a target where one wishes to link with the Fortran compiler:
```meson
executable(..., link_language : 'fortran')
```

A specific case this option fixes is where for example the main program is Fortran that calls C and/or C++ code.
The automatic language detection of Meson prioritizes C/C++, and so an compile-time error results like `undefined reference to `main'`, because the linker is C or C++ instead of Fortran, which is fixed by this per-target override.

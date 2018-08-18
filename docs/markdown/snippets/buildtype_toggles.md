## Toggles for build type, optimization and vcrt type

Since the very beginning Meson has provided different project types to
use, such as *debug* and *minsize*. There is also a *plain* type that
adds nothing by default but instead makes it the user's responsibility
to add everything by hand. This works but is a bit tedious.

In this release we have added new new options to manually toggle
e.g. optimization levels and debug info so those can be changed
independently of other options. For example by default the debug
buildtype has no optmization enabled at all. If you wish to use GCC's
`-Og` instead, you could set it with the following command:

```
meson configure -Doptimization=g
```

Similarly we have added a toggle option to select the version of
Visual Studio C runtime to use. By default it uses the debug runtime
DLL debug builds and release DLL for release builds but this can be
manually changed with the new base option `b_vscrt`.

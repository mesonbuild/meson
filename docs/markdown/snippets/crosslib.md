## Libdir defaults to `lib` when cross compiling

Previously `libdir` defaulted to the value of the build machine such
as `lib/x86_64-linux-gnu`, which is almost always incorrect when cross
compiling. It now defaults to plain `lib` when cross compiling. Native
builds remain unchanged and will point to the current system's library
dir.

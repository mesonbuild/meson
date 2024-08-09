## Zig 0.11 can be used as a C/C++ compiler frontend

Zig offers
[a C/C++ frontend](https://andrewkelley.me/post/zig-cc-powerful-drop-in-replacement-gcc-clang.html) as a drop-in replacement for Clang. It worked fine with Meson up to Zig 0.10. Since 0.11, Zig's
dynamic linker reports itself as `zig ld`, which wasn't known to Meson. Meson now correctly handles
Zig's linker.

You can use Zig's frontend via a [machine file](Machine-files.md):

```ini
[binaries]
c = ['zig', 'cc']
cpp = ['zig', 'c++']
ar = ['zig', 'ar']
ranlib = ['zig', 'ranlib']
lib = ['zig', 'lib']
dlltool = ['zig', 'dlltool']
```

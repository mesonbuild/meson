## New method to handle GNU and Windows symbol visibility for C/C++/ObjC/ObjC++

Defining public API of a cross platform C/C++/ObjC/ObjC++ library is often
painful and requires copying macro snippets into every projects, typically using
`__declspec(dllexport)`, `__declspec(dllimport)` or
`__attribute__((visibility("default")))`.

Meson can now generate a header file that defines exactly what's needed for
all supported platforms:
[`snippets.symbol_visibility_header()`](Snippets-module.md#symbol_visibility_header).

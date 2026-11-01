## Added support for Zig's builtin Windows Resource Compiler

Using `zig rc` as `windres` no longer triggers the error `Could not determine
type of Windows resource compiler`.

Note: Zig 0.14.1 and later have modified their CLI for Meson compatibility, so
this change is only relevant when using `zig rc` versions earlier than 0.14.1.

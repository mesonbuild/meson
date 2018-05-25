## New base build option for LLVM (Apple) bitcode support

When building with clang on macOS, you can now build your static and shared
binaries with embedded bitcode by enabling the `b_bitcode` [base
option](Builtin-options.md#Base_options) by passing `-Db_bitcode=true` to
Meson.

This is better than passing the options manually in the environment since Meson
will automatically disable conflicting options such as `b_asneeded`, and will
disable bitcode support on targets that don't support it such as
`shared_module()`.

Since this requires support in the linker, it is currently only enabled when
using Apple ld. In the future it can be extended to clang on other platforms
too.

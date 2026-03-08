## `werror=true` now applies to the linker as well

When `werror=true` is set, Meson now passes the appropriate
fatal-warnings flag to the linker (for example `--fatal-warnings`
for GNU ld, `-fatal_warnings` for Apple ld, `/WX` for MSVC link).
Previously, `werror=true` only affected compiler warnings.

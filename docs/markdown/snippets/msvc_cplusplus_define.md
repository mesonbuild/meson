## MSVC now sets the __cplusplus #define accurately

For reasons, MSVC will always return `199711L` for `__cplusplus`, even when a
newer c++ standard is explicitly requested, unless you pass a specific option to
the compiler for MSVC 2017 15.7 and newer. Older versions are unaffected by
this. Meson now always sets the option if it is available, as it is unlikley
that users want the default behavior.

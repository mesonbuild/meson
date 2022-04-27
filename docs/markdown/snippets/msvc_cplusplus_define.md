## MSVC now sets the __cplusplus #define accurately

MSVC will always return `199711L` for `__cplusplus`, even when a newer c++
standard is explicitly requested, unless you pass a specific option to the
compiler for MSVC 2017 15.7 and newer. Older versions are unaffected by this.

Microsoft's stated rationale is that "a lot of existing code appears to depend
on the value of this macro matching 199711L", therefore for compatibility with
such (MSVC-only) code they will require opting in to the standards-conformant
value.

Meson now always sets the option if it is available, as it is unlikely that
users want the default behavior, and *impossible* to use the default behavior
in cross-platform code (which frequently breaks as soon as the first person
tries to compile using MSVC).

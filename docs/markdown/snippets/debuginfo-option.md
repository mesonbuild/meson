## New built-in option `b_debuginfo` with a default value `from_buildtype`

This option allows one to explicitly control the debug info format for the build.
When using MSVC-like compilers, `b_debuginfo=embedded` will result in `/Z7`,
`b_debuginfo=standalone` will result in `/Zi`, and `b_debuginfo=edit-and-continue`
will result in `/ZI`. The option currently doesn't have any effect when using 
other compilers.

The default value, `from_buildtype`, produces backward compatible behavior that 
existed prior to the introduction of this option.

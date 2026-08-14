## Per-subproject language arguments are now applied

Compiler and linker arguments set for a specific subproject, for example
`-Dsub:c_args=-DFOO` on the command line or `c_args` in the
`default_options` of a `subproject()` call, are now added to the compile
and link commands of that subproject's targets. Previously such values
were accepted and stored but silently ignored.

Similarly, `<lang>_args` and `<lang>_link_args` entries in a target's
`override_options` now take effect.

In all cases the per-subproject or per-target value replaces the global
value (including flags coming from environment variables such as
`CFLAGS`), it is not appended to it. This matches what
`get_option('c_args')` already returned inside a subproject.

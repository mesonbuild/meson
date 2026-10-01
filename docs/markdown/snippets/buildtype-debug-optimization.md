## Consistent handling of `buildtype`, `debug` and `optimization`

This version of Meson handles more consistently cases in which `buildtype`
is set at the same time as `debug` and `optimization`.  In particular,
when `debug` or `optimization` are also set explicitly by the same source,
for example in the same machine file or in the same `default_options`,
the explicit value now takes precedence, independent of the order in
which the options are listed.  Previously this was only the case on
the command line; in machine files and `default_options`, a `buildtype`
listed after `debug` or `optimization` would override them.

In addition, a `buildtype` set for a specific subproject, for example
with `-Dsubproj:buildtype=debug`, now also overrides values of `debug`
and `optimization` from the subproject's own `default_options`, in the
same way as a `buildtype` set for the toplevel project overrides the
toplevel project's `default_options`.  A global `buildtype`, such as
`-Dbuildtype=debug`, still does not override `optimization` or `debug`
from a subproject's `default_options`.

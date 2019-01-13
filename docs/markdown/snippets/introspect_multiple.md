## Added option to introspect multiple parameters at once

Meson introspect can now print the results of multiple introspection
commands in a single call. The results are then printed as a single JSON
object.

The format for a single command was not changed to keep backward
compatibility.

Furthermore the option `-a,--all`, `-i,--indent` and `-f,--force-object-output`
were added to print all introspection information in one go, format the
JSON output (the default is still compact JSON) and force use the new
output format, even if only one introspection command was given.

A complete introspection dump is also stored in the `meson-info`
directory. This dump will be (re)generated each time meson updates the
configuration of the build directory.

Additionlly the format of `meson introspect target` was changed:

  - New: the `sources` key. It stores the source files of a target and their compiler parameters.
  - New: the `defined_in` key. It stores the meson file where a target is defined
  - Added new target types (`jar`, `shared module`).

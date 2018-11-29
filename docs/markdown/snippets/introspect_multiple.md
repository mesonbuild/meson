## Added option to introspect multiple parameters at once

Meson introspect can now print the results of multiple introspection
commands in a single call. The results are then printed as a single JSON
object.

The format for a single command was not changed to keep backward
compatibility.

Furthermore the option `-a,--all`, `-i,--indent` and `-f,--force-new`
were added to print all introspection information in one go, format the
JSON output (the default is still compact JSON) and foce use the new
output format, even if only one introspection command was given.

Additionlly the format of target was changed:
  - `filename` is now a list of output filenames
  - `install_filename` is now also a list of installed files
  - New: the `sources` key. It stores the source files of a target and there compiler parameters

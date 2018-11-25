## Added option to introspect multiple parameters at once

Meson introspect can now print the results of multiple parameters
in a single call. The results are then printed as a single JSON
object.

The format for a single command was not changed to keep backward
compatibility.

Furthermore the option `-a,--all` and `-i,--indent` was added to
print all introspection information in one go and format the
JSON output (the default is still compact JSON).
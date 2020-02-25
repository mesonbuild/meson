## Summary improvements

A new `list_sep` keyword argument has been added to `summary()` function.
If defined and the value is a list, elements will be separated by the provided
string instead of being aligned on a new line.

The automatic `subprojects` section now also print the number of warnings encountered
during that subproject configuration, or the error message if the configuration failed.

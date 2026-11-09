## Changes to `default_options` are applied when reconfiguring

Previously, the `default_options` of `project()`, `subproject()` and
`dependency()` were only used when a project or subproject was configured
for the first time; changing them had no effect on an existing build
directory.  Now, options are computed again every time Meson reconfigures
the build directory, so that changes to `default_options` are picked up,
and removing an entry from `default_options` restores the default value.

Machine files are *not* reread unless the project is reconfigured
from scratch (such as with `--wipe`).  In particular, unlike previous
versions of Meson, adding a new subproject will *not* read the relevant
option sections of the machine file, and will instead use the values that
the machine file had when the project was first configured.

This change fixed other bugs as a side effect.  For example, removing an
option from the command line, for example with `meson configure -Uname`,
now makes the value from `default_options` effective again.

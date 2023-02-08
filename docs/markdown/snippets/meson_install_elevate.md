## `meson install` now supports user-preferred root elevation tools

Previously, when installing a project, if any files could not be installed due
to insufficient permissions the install process was automatically re-run using
polkit. Now it prompts to ask whether that is desirable, and checks for
CLI-based tools such as sudo or opendoas or `$MESON_ROOT_CMD`, first.

Meson will no longer attempt privilege elevation at all, when not running
interactively.

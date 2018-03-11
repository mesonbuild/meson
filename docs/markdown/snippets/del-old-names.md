## Old command names are now errors

Old executable names `mesonintrospect`, `mesonconf`, `mesonrewriter`
and `mesontest` have been deprecated for a long time. Starting from
this versino they no longer do anything but instead always error
out. All functionality is available as subcommands in the main `meson`
binary.

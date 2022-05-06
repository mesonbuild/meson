## Update all wraps from WrapDB with `meson wrap update` command

The command `meson wrap update`, with no extra argument, will now update all wraps
that comes from WrapDB to the latest version. The extra `--force` argument will
also replace wraps that do not come from WrapDB if one is available.

The command `meson subprojects update` will not download new wrap files from
WrapDB any more.

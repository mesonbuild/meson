## Wraps from subprojects are automatically promoted

It is not required to promote wrap files for subprojects into the main project
any more. When configuring a subproject, meson will look for any wrap file or
directory in the subproject's `subprojects/` directory and add them into the
global list of available subprojects, to be used by any future `subproject()`
call or `dependency()` fallback. If a subproject with the same name already exists,
the new wrap file or directory is ignored. That means that the main project can
always override any subproject's wrap files by providing their own, it also means
the ordering in which subprojects are configured matters, if 2 subprojects provide
foo.wrap only the one from the first subproject to be configured will be used.

This new behavior can be disabled by passing `--wrap-mode=nopromote`.

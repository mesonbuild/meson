## Only shared libraries are added to `PATH` for tests and `meson devenv` on Windows

On Windows, the directories of the shared libraries that an executable links to
are added to `PATH` when running tests and in `meson devenv`.  The directories
of other targets listed in `depends` or in the test arguments, for example
a `custom_target()`, were also added.  This was not intended and could cause
the wrong DLL to be found.  Now only the directories containing
`shared_library()` targets, and the shared libraries that they depend on, are
added.

A project that relied on a `custom_target()` output directory being in `PATH`
should add that directory to the test environment explicitly.

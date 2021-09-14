## Add `-B` option to all subcommands that needs a build directory

Some commands are accepting either sourcedir or builddir as positional
argument, others have the -C argument for the build directory. For
consistency across all commands, -B now always refers to the build
directory, everywhere.

This also fix poorly defined behaviour of -C which commonly mean "cd
into this directory first". That's too vague and does not describe what
it actually mean; reading file there? writing files there? workdir for
subprocesses? Most Meson commands does not actually chdir and used -C to
actually mean "the build directory". Using -B is now much more explicit
for that.

Example:
```meson
meson setup -B builddir -Dfoo=bar
meson configure -B builddir -Dfoo=baz
meson compile -B builddir
meson install -B builddir
```

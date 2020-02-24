## Backend agnostic compile command

A new `meson compile` command has been added to support backend agnostic
compilation. It accepts two arguments, `-j` and `-l`, which are used if
possible (`-l` does nothing with msbuild). A `-j` or `-l` value < 1 lets the
backend decide how many threads to use. For msbuild this means `-m`, for
ninja it means passing no arguments.

```console
meson builddir --backend vs
meson compile -C builddir -j0  # this is the same as `msbuild builddir/my.sln -m`
```

```console
meson builddir
meson compile -C builddir -j3  # this is the same as `ninja -C builddir -j3`
```

Additionally `meson compile` provides a `--clean` switch to clean the project.

A complete list of arguments is always documented via `meson compile --help`

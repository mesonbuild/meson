## Android cross file generator

The `env2mfile` command now supports a `--android` argument. When
specified, it tells the cross file generator to create cross files for
all Android toolchains located on the current machines.

This typically creates many files, so the `-o` argument specifies the
output directory. A typical use case goes like this:

```
meson env2mfile --android -o androidcross
meson setup --cross-file \
  androidcross/android-29.0.14033849-android35-aarch64-cross.txt \
  builddir
```

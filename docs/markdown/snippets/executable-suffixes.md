## Target names for executables now take into account suffixes.

In previous versions of meson, a `meson.build` file like this:

```
exectuable('foo', 'main.c')
exectuable('foo', 'main.c', name_suffix: 'bar')
```

would result in a configure error because meson internally used
the same id for both executables. This build file is now allowed
since meson takes into account the `bar` suffix when generating the
second executable. This allows for executables with the same basename
but different suffixes to be built in the same subdirectory.

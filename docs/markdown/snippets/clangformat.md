## A builtin target to run clang-format

If you have `clang-format` installed and there is a `.clang-format`
file in the root of your master project, Meson will generate a run
target called `clang-format` so you can reformat all files with one
command:

```meson
ninja clang-format
```


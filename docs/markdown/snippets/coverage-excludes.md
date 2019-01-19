## Exclude files and folders from coverage reports

Using the built-in option `excludes` it's now possible for the user to define
files and folders they want excluded from coverage reports. Any subproject code
is excluded automatically just like before. The `excludes` option takes a comma
separated list of files and folders to exclude from all coverage reports. In
order to exclude the folder `some_folder` and the file `src/some_file.c`,
configure the `excludes` option accordingly:

```console
$ meson configure -Dexcludes=some_folder,src/some_file.c
```

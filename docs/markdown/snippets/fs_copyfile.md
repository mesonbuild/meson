## `fs.copyfile` to replace `configure_file(copy : true)`

A new method has been added to the `fs` module, `copyfile`. This method replaces
`configure_file(copy : true)`, but only copies files. Unlike `configure_file()`
it runs at build time, and the output name is optional defaulting to the
filename without paths of the input if unset:

```meson
fs.copyfile('src/file.txt')
```
Will create a file in the current build directory called `file.txt`


```meson
fs.copyfile('file.txt', 'outfile.txt')
```
Will create a copy renamed to `outfile.txt`

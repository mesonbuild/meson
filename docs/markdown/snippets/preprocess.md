## New method to preprocess source files

Compiler object has a new `preprocess()` method. It is supported by all C/C++
compilers. It preprocess sources without compiling them.

The preprocessor will receive the same arguments (include directories, defines,
etc) as with normal compilation. That includes for example args added with
`add_project_arguments()`, or on the command line with `-Dc_args=-DFOO`.

```meson
cc = meson.get_compiler('c')
pp_files = cc.preprocess('foo.c', 'bar.c', output: '@PLAINNAME@')
exe = executable('app', pp_files)
```

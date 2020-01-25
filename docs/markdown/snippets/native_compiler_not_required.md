## Native (build machine) compilers not always required by `project()`

When cross-compiling, native (build machine) compilers for the languages
specified in `project()` are not required, if no targets use them.

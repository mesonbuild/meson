## `add_project_dependencies()` function

Dependencies can now be added to all build products using
`add_project_dependencies()`.  This can be useful in several
cases:

* with special dependencies such as `dependency('threads')`
* with system libraries such as `find_library('m')`
* with the `include_directories` keyword argument of
`declare_dependency()`, to add both source and build
directories to the include search path

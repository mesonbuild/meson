## library vs_module_defs may be an array

It is sometimes desirable to use a .def file only in some situations, such as
with msvc, but now with mingw. Previously this meant defining a duplicate
library() call with the `vs_module_defs` keyword argument added. Now an array
may be passed, including an empty one, which acts like not passing the argument.

Only the first member of the array will be used, the others will be discarded
with a warning.

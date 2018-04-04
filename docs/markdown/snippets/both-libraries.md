## Building both shared and static libraries

A new function `both_libraries()` has been added to build both shared and static
libraries at the same time. Source files will be compiled only once and object
files will be reused to build both shared and static libraries, unless
`b_staticpic` user option or `pic` argument are set to false in which case
sources will be compiled twice.

The returned `buildtarget` object always represents the shared library.

A new `module` keyword argument has been added to `library()` and
`both_libraries()` functions to build a `shared_module()` instead of the shared
library. This is useful to build a module that can also be statically linked.

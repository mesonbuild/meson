## New [[local_program]] function

Similar to [[find_program]], but only work with a program that exists in
source tree, or a built target. Meson will not look for the program in the
system or in a subproject.

In addition, `depends` keyword argument can be specified in case the program
depends on built targets, for example a Python script could require a compiled
C module. If any such dependency is present, the program can only be used in
build-time commands (e.g. [[custom_target]]).

The program can be passed to [[meson.override_find_program]] and used in
subprojects.

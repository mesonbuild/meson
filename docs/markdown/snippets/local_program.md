## New [[local_program]] function

It is similar to [[find_program]] but only work with a local program
(source or build tree) that exists at configure time. The program will not be
looked on the system or from subproject overrides.

In addition, `depends` and `depend_files` keyword arguments can be specified
in the case the program depends on built targets. For example a python script
that requires a compiled C module. When specified, the program can only be used
in build-time commands (e.g. [[custom_target]]).

The program can be passed to [[meson.override_find_program]] and used in
subprojects.

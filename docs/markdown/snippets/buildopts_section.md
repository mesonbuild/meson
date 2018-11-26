## New `section` key for the buildoptions introspection

Meson now has a new `section` key in each build option. This allows
IDEs to group these options similar to `meson configure`.

The possible values for `section` are:

 - core
 - backend
 - base
 - compiler
 - directory
 - user
 - test

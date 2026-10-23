## `meson.override_find_program` can be called multiple times for the same name and program

Meson now allows overriding the same program twice if both calls refer
to the same executable.  This makes it easier to override a program
for both `native: true` and `native: false`, if its output is
target-independent.

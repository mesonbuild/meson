---
short-description: Style recommendations for Meson files
...

# Style recommendations

This page lists some recommendations on organizing and formatting your
Meson build files.

## Tabs or spaces?

Always spaces.

## Naming options

There are two ways of naming project options. As an example for
booleans the first one is `foo` and the second one is
`enable-foo`. The former style is recommended, because in Meson
options have strong type, rather than being just strings.

You should try to name options the same as is common in other
projects. This is especially important for yielding options, because
they require that both the parent and subproject options have the same
name.

# Global arguments

Prefer `add_project_arguments` to `add_global_arguments` because using
the latter prevents using the project as a subproject.

# Cross compilation arguments

Try to keep cross compilation arguments away from your build files as
much as possible. Keep them in the cross file instead. This adds
portability, since all changes needed to compile to a different
platform are isolated in one place.

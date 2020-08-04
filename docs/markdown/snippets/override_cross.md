## `meson.override_*` respects `native` keyword argument

Firstly, `override_find_program` takes a `native` keyword argument just like
`override_dependency`.  Secondly, both will complain during if the argument and
the override's own keyword argument do not match.

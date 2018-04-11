## New feature option type

A new type of option can be defined in `meson_options.txt` for the traditional
`enabled / disabled / auto` tristate. The value of this option can be passed to
the `required` keyword argument of functions `dependency()`, `find_library()`,
`find_program()` and `add_languages()`.

A new global option `auto_features` has been added to override the value of all
`auto` features. It is intended to be used by packagers to have full control on
which feature must be enabled or disabled.

## Yielding subproject option to superproject

Normally project options are specific to the current project. However
sometimes you want to have an option whose value is the same over all
projects. This can be achieved with the new `yield` keyword for
options. When set to `true`, getting the value of this option in
`meson.build` files gets the value from the option with the same name
in the master project (if such an option exists).

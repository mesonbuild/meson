## Integer options

There is a new integer option type with optional minimum and maximum
values. It can be specified like this in the `meson_options.txt` file:

    option('integer_option', type : 'integer', min : 0, max : 5, value : 3)

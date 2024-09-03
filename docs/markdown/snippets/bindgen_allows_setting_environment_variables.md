## Bindgen now allows customizing environment variables

Bindgen is configurable through environment variables on how it searches for
clang and what extra arguments it passes to the compiler. The bindgen() function
of the rust module now accepts an `env` keyword argument for customizing
environment variables. The type of the argument is the same as `env` of
[[custom_target]].

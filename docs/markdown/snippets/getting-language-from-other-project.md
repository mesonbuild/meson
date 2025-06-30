## Using `meson.get_compiler()` to get a language from another project is marked broken

Meson currently will return a compiler instance from the `meson.get_compiler()`
call, if that language has been initialized in any project. This can result in
situations where a project can only work as a subproject, or if a dependency is
provided by a subproject rather than by a pre-built dependency.

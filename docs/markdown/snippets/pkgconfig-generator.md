## Improvements to pkgconfig module

A `StaticLibrary` or `SharedLibrary` object can optionally be passed
as first positional argument of the `generate()` method. If one is provided a
default value will be provided for all required fields of the pc file:
- `install_dir` is set to `pkgconfig` folder in the same location than the provided library.
- `description` is set to the project's name followed by the library's name.
- `name` is set to the library's name.

Generating a .pc file is now as simple as:

```
pkgconfig.generate(mylib)
```

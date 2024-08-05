## Add way to get Vala GIR file

Our current recomendation is to create a string via `meson.current_build_dir() /
Foo-1.0.gir`, which is not the Meson way. A new `BuildTarget.get_gir()` method
has been added which returns a `File` object pointing to the GIR file.

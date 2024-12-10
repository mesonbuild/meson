## Basic support for RGBDS assembly

Meson now provides basic support for the assembly
and linking of Game Boy and Game Boy Color games
with RGBDS.

Most projects will still need to call `rgbfix` as
a `custom_target` as this time, unless they have
correct header values in assembly source.

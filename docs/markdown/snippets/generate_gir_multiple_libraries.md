## gnome.generate_gir() now optionally accepts multiple libraries

The GNOME module can now generate a single gir for multiple libraries, which
is something `g-ir-scanner` supported, but had not been exposed yet.

gnome.generate_gir() will now accept multiple positional arguments, if none
of these arguments are an `Executable` instance.

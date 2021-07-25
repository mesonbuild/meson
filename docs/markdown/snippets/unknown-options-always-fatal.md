## Unknown options are now always fatal

Passing unknown options to "meson setup" or "meson configure" is now
always fatal. That is, Meson will exit with an error code if this
happens. Previous Meson versions only showed a warning message.

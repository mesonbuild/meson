## Unity build with Vala disabled

The approach that meson has used for Vala unity builds is incorrect, we
combine the generated C files like we would any other C file. This is very
fragile however, as the Vala compiler generates helper functions and macros
which work fine when each file is a separate translation unit, but fail when
they are combined.

## Swift compiler receives select C family compiler options

Meson now passes select few C family (C/Obj-C) compiler options to the
Swift compiler, notably *-std=*, in order to improve the compatibility
of C code as interpreted by the C compiler and the Swift compiler.

NB: This does not include any of the options set in the target's
c_flags.

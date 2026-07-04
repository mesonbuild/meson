## Vala cross compilation changes

Traditionally Meson has used the same Vala compiler for cross and
native compilation. It turned out that even though the Vala compiler
generated C code, the output and its dependencies are platform
dependent. Now Meson uses Vala in the same way as all other cross
compilers and it can be defined in the cross file.

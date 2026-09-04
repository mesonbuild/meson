## New `b_freestanding` base option

The new `b_freestanding` base option tells supported compilers that targets do
not assume a hosted standard library. GCC-compatible C-family compilers receive
`-ffreestanding`, while clang-cl receives `/clang:-ffreestanding`.

## Support for overiding the linker with ldc

LDC (the llvm D compiler) now honors D_LD linker variable (or d_ld in the cross
file) and is able to pick differnt linkers. ld.bfd, ld.gold, ld.lld, ld64,
link, and lld-link are currently supported.

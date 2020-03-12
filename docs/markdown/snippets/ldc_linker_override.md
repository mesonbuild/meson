## Support for overiding the linker with ldc and gdc

LDC (the llvm D compiler) and GDC (The Gnu D Compiler) now honor D_LD linker
variable (or d_ld in the cross file) and is able to pick differnt linkers.

GDC supports all of the same values as GCC, LDC supports ld.bfd, ld.gold,
ld.lld, ld64, link, and lld-link.

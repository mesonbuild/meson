## Support for Clang-based Borland C++ Toolchain

Meson now recognizes the [Clang-based Borland C++ compiler family](https://docwiki.embarcadero.com/RADStudio/Athens/en/Clang-enhanced_C++_Compilers),
targeting `i686-pc-windows-omf` and `x86_64-pc-windows-elf`, as `bccclang`.

There are certain limitations when using this toolchain:

- Creating static libraries with the same object names in different directories
  does not work. This is an issue in `tlib`, and a possible workaround is to
  use the `prelink` option when creating your library.
- `ilink` always allows undefined symbols.
- Building VCL applications or linking with Delphi code is untested.

Note that the newer `bcc64x` compiler (named "Windows 64-bit (modern)" in RAD
Studio) is COFF-based. It behaves more like upstream Clang in a MinGW
environment, so it is identified as normal `clang`.

Previously, `bcc64x`'s linker was incorrectly identified as `ld.bfd`. Now it
resolves to `ld.lld` correctly.

## Support for LLVM-based flang compiler

Added basic handling for the [flang](https://flang.llvm.org/docs/) compiler
that's now part of LLVM. It is the successor of another compiler named
[flang](https://github.com/flang-compiler/flang) by largely the same
group of developers, who now refer to the latter as "classic flang".

Meson already supports classic flang, and the LLVM-based flang now
uses the compiler-id `'llvm-flang'`.

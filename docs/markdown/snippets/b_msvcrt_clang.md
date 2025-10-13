## `-Db_msvcrt` on clang

`-Db_msvcrt` will now link the appropriate runtime library, and set
the appropriate preprocessor symbols, also when the compiler is clang.
This is only supported when using `link.exe` or `lld-link.exe` as the
linker.

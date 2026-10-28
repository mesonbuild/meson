## Added support for the Small Device C Compiler (SDCC)

Meson can now detect and use `sdcc` to compile C code for small 8-bit
microcontrollers.  Static libraries are created with `sdar`, and executables are
produced in the Intel HEX (`.ihx`) format.  The new CPU families `f8`, `hc08`,
`mcs51`, `padauk`, `stm8` and `z80` are recognized in cross files.

SDCC selects the target architecture with the `-m` option, which must be
passed both when compiling and when linking.  Add it to the `c` entry of the
`[binaries]` section so that it is used for all invocations of the compiler.
See `cross/sdcc-mcs51.txt` for an example:

```ini
[binaries]
c = ['sdcc', '-mmcs51']

[host_machine]
system = 'bare metal'
cpu_family = 'mcs51'
cpu = 'mcs51'
endian = 'little'
```

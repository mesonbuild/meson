## CC-RX compiler for C and CPP

Cross-compilation is now supported for Renesas RX targets with the CC-RX compiler.

The environment path should be set properly for the CC-RX compiler executables.
The `-cpu` option with the appropriate value should be mentioned in the cross-file as shown in the snippet below.

```ini
[properties]
c_args      = ['-cpu=rx600']
cpp_args    = ['-cpu=rx600']
```

The default extension of the executable output is `.abs`.
Other target specific arguments to the compiler and linker will need to be added explicitly from the cross-file(`c_args`/`c_link_args`/`cpp_args`/`cpp_link_args`) or some other way.
Refer to the CC-RX User's manual for additional compiler and linker options.
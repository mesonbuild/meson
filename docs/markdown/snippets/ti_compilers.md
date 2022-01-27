## Added support for Texas Instruments MSP430 and ARM compilers

Meson now supports the TI [MSP430](https://www.ti.com/tool/MSP-CGT) and
[ARM](https://www.ti.com/tool/ARM-CGT) toolchains. The compiler and linker are
identified as `ti` and `ti-ar`, respectively. To maintain backwards
compatibility with existing build definitions, the [C2000
toolchain](https://www.ti.com/tool/C2000-CGT) is still identified as `c2000` and
`ar2000`.

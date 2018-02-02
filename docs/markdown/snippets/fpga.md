## Experimental FPGA support

This version adds support for generating, analysing and uploading FPGA
programs using the [IceStorm
toolchain](http://www.clifford.at/icestorm/). This support is
experimental and is currently limited to the `iCE 40` series of FPGA
chips.

FPGA generation integrates with other parts of Meson seamlessly. As an
example, [here](https://github.com/jpakkane/lm32) is an example
project that compiles a simple firmware into Verilog and combines that
with an lm32 softcore processor.

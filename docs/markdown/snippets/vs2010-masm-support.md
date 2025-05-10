## Support for MASM in Visual Studio backends

Previously, assembling `.masm` files with Microsoft's Macro Assembler is only
available on the Ninja backend. This now also works on Visual Studio backends.

Note that building ARM64EC code using `ml64.exe` is currently unimplemented in
both of the backends. If you need mixing x64 and Arm64 in your project, please
file an issue on GitHub.

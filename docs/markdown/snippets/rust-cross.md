## Rust cross-compilation

Cross-compilation is now supported for Rust targets. Like other
cross-compilers, the Rust binary must be specified in your cross
file. It should specify a `--target` (as installed by `rustup target`)
and a custom linker pointing to your C cross-compiler. For example:

```
[binaries]
c = '/usr/bin/arm-linux-gnueabihf-gcc-7'
rust = [
    'rustc',
    '--target', 'arm-unknown-linux-gnueabihf',
    '-C', 'linker=/usr/bin/arm-linux-gnueabihf-gcc-7',
]
```

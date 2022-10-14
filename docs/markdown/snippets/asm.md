## New languages: `nasm` and `masm`

When the `nasm` language is added to the project, `.asm` files are
automatically compiled with NASM. This is only supported for x86 and x86_64 CPU
family. `yasm` is used as fallback if `nasm` command is not found.

When the `masm` language is added to the project, `.masm` files are
automatically compiled with Microsoft's Macro Assembler. This is only supported
for x86, x86_64, ARM and AARCH64 CPU families.

Note that GNU Assembly files usually have `.s` or `.S` extension and were already
built using C compiler such as GCC or CLANG.

```meson
project('test', 'nasm')

exe = executable('hello', 'hello.asm')
test('hello', exe)
```

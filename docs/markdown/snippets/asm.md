## New language `nasm`

When the `nasm` language is added to the project, `.asm` files are
automatically compiled with NASM. This is only supported for x86 and x86_64 CPU
family. `yasm` is used as fallback if `nasm` command is not found.

Note that GNU Assembly files usually have `.s` extension and were already built
using C compiler such as GCC or CLANG.

```meson
project('test', 'nasm')

exe = executable('hello', 'hello.asm')
test('hello', exe)
```

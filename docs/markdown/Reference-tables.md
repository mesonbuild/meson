# Reference tables

## Compiler ids

These are return values of the `get_id` method in a compiler object.

| Value     | Compiler family                |
| -----     | ----------------               |
| gcc       | The GNU Compiler Collection    |
| clang     | The Clang compiler             |
| msvc      | Microsoft Visual Studio        |
| intel     | Intel compiler                 |
| llvm      | LLVM-based compiler (Swift, D) |
| mono      | Xamarin C# compiler            |
| dmd       | D lang reference compiler      |
| rustc     | Rust compiler                  |
| valac     | Vala compiler                  |
| pathscale | The Pathscale Fortran compiler |
| pgi       | The Portland Fortran compiler  |
| sun       | Sun Fortran compiler           |
| g95       | The G95 Fortran compiler       |
| open64    | The Open64 Fortran Compiler    |
| nagfor    | The NAG Fortran compiler       |
| lcc       | Elbrus C/C++/Fortran Compiler  |
| arm       | ARM compiler                   |
| armclang  | ARMCLANG compiler              |

## Script environment variables

| Value               | Comment                         |
| -----               | -------                         |
| MESON_SOURCE_ROOT   | Absolute path to the source dir |
| MESON_BUILD_ROOT    | Absolute path to the build dir  |
| MESONINTROSPECT     | Command to run to run the introspection command, may be of the form `python /path/to/meson introspect`, user is responsible for splitting the path if necessary. |
| MESON_SUBDIR        | Current subdirectory, only set for `run_command` |

## CPU families

These are returned by the `cpu_family` method of `build_machine`,
`host_machine` and `target_machine`. For cross compilation they are
set in the cross file.

| Value               | Comment                         |
| -----               | -------                         |
| x86                 | 32 bit x86 processor  |
| x86_64              | 64 bit x86 processor  |
| ia64                | Itanium processor     |
| arm                 | 32 bit ARM processor  |
| aarch64             | 64 bit ARM processor  |
| mips                | 32 bit MIPS processor |
| mips64              | 64 bit MIPS processor |
| ppc                 | 32 bit PPC processors |
| ppc64               | 64 bit PPC processors |
| e2k                 | MCST Elbrus processor |
| parisc              | HP PA-RISC processor  |
| riscv32             | 32 bit RISC-V Open ISA|
| riscv64             | 64 bit RISC-V Open ISA|
| sparc64             | SPARC v9 processor    |

Any cpu family not listed in the above list is not guaranteed to
remain stable in future releases.

## Operating system names

These are provided by the `.system()` method call.

| Value               | Comment                         |
| -----               | -------                         |
| linux               | |
| darwin              | Either OSX or iOS |
| windows             | Any version of Windows |
| cygwin              | The Cygwin environment for Windows |
| haiku               | |
| freebsd             | FreeBSD and its derivatives |
| dragonfly           | DragonFly BSD |
| netbsd              | |

Any string not listed above is not guaranteed to remain stable in
future releases.


## Language arguments parameter names

These are the parameter names for passing language specific arguments to your build target.

| Language      | Parameter name |
| -----         | ----- |
| C             | c_args |
| C++           | cpp_args |
| C#            | cs_args |
| D             | d_args |
| Fortran       | fortran_args |
| Java          | java_args |
| Objective C   | objc_args |
| Objective C++ | objcpp_args |
| Rust          | rust_args |
| Vala          | vala_args |
